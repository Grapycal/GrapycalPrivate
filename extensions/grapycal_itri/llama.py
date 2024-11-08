from pathlib import Path
from grapycal import Node, param, func
from typing import Callable, Optional
from grapycal.sobjects.node import background_task
from grapycal.sobjects.port import InputPort
from objectsync.sobject import SObjectSerialized
from transformers.models.llama.modeling_llama import LlamaForCausalLM
from transformers.tokenization_utils import PreTrainedTokenizer
from modelscope import snapshot_download , AutoTokenizer
from transformers import AutoModelForCausalLM,BitsAndBytesConfig, TrainerCallback
import torch
from peft import LoraConfig
from peft.utils.peft_types import TaskType

from transformers import TrainingArguments

from transformers import Trainer, DataCollatorForSeq2Seq
from transformers.trainer_callback import TrainerControl, TrainerState


def data_proc(tokenizer: PreTrainedTokenizer, instruction_str:str, input_str:str, output_str:str):
    MAX_LENGTH = 384    # Llama分词器会将一个中文字切分为多个token，因此需要放开一些最大长度，保证数据的完整性
    input_ids, attention_mask, labels = [], [], []
    instruction = tokenizer(f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n請回答問題。<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{instruction_str + input_str}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n", add_special_tokens=False)  # add_special_tokens 不在开头加 special_tokens
    response = tokenizer(f"{output_str}<|eot_id|>", add_special_tokens=False)
    input_ids = instruction["input_ids"] + response["input_ids"] + [tokenizer.pad_token_id]
    attention_mask = instruction["attention_mask"] + response["attention_mask"] + [1]  # 因为eos token咱们也是要关注的所以 补充为1
    labels = [-100] * len(instruction["input_ids"]) + response["input_ids"] + [tokenizer.pad_token_id]  
    if len(input_ids) > MAX_LENGTH:  # 做一个截断
        input_ids = input_ids[:MAX_LENGTH]
        attention_mask = attention_mask[:MAX_LENGTH]
        labels = labels[:MAX_LENGTH]
    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels
    }

class OutputCallback(TrainerCallback):
    def __init__(self, callback:Callable) -> None:
        super().__init__()
        self.callback = callback
    def on_log(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        self.callback(control, state)

class LLaMA3Node(Node):
    category = 'torch'
    label = 'LLaMA3'

    def build_node(self):
        self.load_btn = self.add_button_control('Load')
        self.stop_training_btn = self.add_button_control('Stop Training')
        self.train_port = self.add_in_port('train with dataset', max_edges=1)
        self.loss_port = self.add_out_port('loss')
        self.epoch_port = self.add_out_port('epoch')
        self.css_classes.append('fit-content')

    def init_node(self):
        self.tokenizer: Optional[PreTrainedTokenizer] = None
        self.model: Optional[LlamaForCausalLM] = None
        self.load_btn.on_click += self.load
        self.train_port.on_activate += self.train
        self.load_btn.label.set('Load')
        self.training = False
        self.stop_training_flag = False
        self.stop_training_btn.on_click += self.stop_training

    def stop_training(self):
        self.stop_training_flag = True

    def output_callback(self, control, state: TrainerState):
        if self.stop_training_flag:
            control.should_training_stop = True
        if 'loss' in state.log_history[-1]:
            self.loss_port.push(state.log_history[-1]['loss'])
            self.epoch_port.push(state.epoch)

    def train(self, port:InputPort) -> None:
        if self.training:
            self.print('Training is already in progress')
            port.get()
            return
        if self.model is None or self.tokenizer is None:
            self.print_exception('Please press the Load button to load the model first')
            port.get()
            return
        
        assert self.model is not None
        assert self.tokenizer is not None

        dataset = []

        port_input = port.get()

        if isinstance(port_input, list) and isinstance(port_input[0], str):
            for data in port_input:
                context = ""
                question = ""
                answer = data
                dataset.append(data_proc(self.tokenizer, context, question, answer))
        else:
            for data in port_input:
                context = data["context"]
                qa_pairs = data["qa_pairs"]
                for question, answer in qa_pairs:
                    dataset.append(data_proc(self.tokenizer, context, question, answer))

        args = TrainingArguments(
            output_dir=str(Path(self.save_dir)/'output'),
            per_device_train_batch_size=self.batch_size,
            gradient_accumulation_steps=4,
            logging_steps=1,
            num_train_epochs=self.num_train_epochs,
            save_steps=self.save_steps, 
            learning_rate=1e-4,
            save_on_each_node=True,
            gradient_checkpointing=True,
            
        )
        trainer = Trainer(
            model=self.model,
            args=args,
            train_dataset=dataset,
            data_collator=DataCollatorForSeq2Seq(tokenizer=self.tokenizer, padding=True),
        )
        
        trainer.add_callback(OutputCallback(self.output_callback))

        import threading

        trainer_thread = threading.Thread(target=self.trainer_thread_task, args=(trainer,))
        trainer_thread.start()

    def trainer_thread_task(self, trainer: Trainer):
        try:
            self.training = True
            self.stop_training_flag = False
            self.set_running(True)
            trainer.train()
        finally:
            self.set_running(False)
            self.training = False

    @param()
    def param(
        self,
        save_dir: str = './llama3',
        batch_size: int = 4, 
        lora_rank:int = 8, 
        lora_alpha:int = 32,
        save_steps:int=100,
        num_train_epochs:int=1,
    ) -> None:
        
        self.save_dir = save_dir
        self.batch_size = batch_size
        self.lora_rank = lora_rank
        self.lora_alpha = lora_alpha
        self.save_steps = save_steps
        self.num_train_epochs = num_train_epochs

    @background_task
    def load(self) -> None:
        if self.training:
            self.print('Cannot load model while training')
            return
        
        if not Path(self.save_dir).exists():
            self.print('Pretrained model not found. Trying to download model...')
            self.download()
        try:
            self.print('Loading model and tokenizer...')
            self.load_btn.label.set('Loading...')
            self.load_()
        except Exception as e:
            self.print_exception(e)
            self.print('Failed to load model and tokenizer. Trying to download model...')
            try:
                self.download()
                self.load_()
            except Exception:
                self.load_btn.label.set('Load')
                raise
        self.load_btn.label.set('Reload')
        self.print('Model and tokenizer loaded.')
    
    def load_(self):
        self.tokenizer = AutoTokenizer.from_pretrained(str(Path(self.save_dir)/'LLM-Research/Meta-Llama-3___1-8B-Instruct'), use_fast=False, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(str(Path(self.save_dir)/'LLM-Research/Meta-Llama-3___1-8B-Instruct'), device_map=torch.device("cuda:0"),torch_dtype=torch.bfloat16, quantization_config=BitsAndBytesConfig(load_in_8bit=True))

        eot = "<|eot_id|>"
        eot_id = self.tokenizer.convert_tokens_to_ids(eot)
        self.tokenizer.pad_token = eot
        self.tokenizer.pad_token_id = eot_id

        config = LoraConfig(
            task_type=TaskType.CAUSAL_LM, 
            #target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            target_modules=['q_proj', 'k_proj', 'v_proj'],
            inference_mode=False,
            r=self.lora_rank,
            lora_alpha=self.lora_alpha,
            lora_dropout=0.1
        )
        self.model.add_adapter(config, "lora")
        self.calculate_param()
        
    def download(self):
        snapshot_download('LLM-Research/Meta-Llama-3.1-8B-Instruct', cache_dir=self.save_dir, revision='master')

    @func()
    def answer(self,system_msg:str='請回答問題',question:str='') -> str:
        if self.training:
            self.print('Cannot answer while training')
            return ''
        if self.model is None or self.tokenizer is None:
            self.print_exception('Please press the Load button to load the model first')
            return ''
        
        messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": question},
        ]
        
        input_ids = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = self.tokenizer([input_ids], return_tensors="pt").to('cuda')
        generated_ids = self.model.generate(model_inputs.input_ids,max_new_tokens=512)
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return response

    def calculate_param(self) -> None:
        """
        Prints the number of trainable parameters in the model.
        """
        trainable_params = 0
        all_param = 0
        for _, param in self.model.named_parameters():
            all_param += param.numel()
            if param.requires_grad:
                trainable_params += param.numel()
        self.print(
            f"trainable params: {trainable_params} || all params: {all_param} || trainable%: {100 * trainable_params / all_param}"
        )
    
    def destroy(self) -> SObjectSerialized:
        if self.training:
            self.stop_training()
        return super().destroy()