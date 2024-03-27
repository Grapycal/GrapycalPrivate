import { EventTopic, IntTopic, StringTopic } from "objectsync-client"
import { Control } from "./control"
import { print } from "../../devUtils"
import { BindInputBoxAndTopic } from "../../ui_utils/interaction"
import { TextBox} from "../../utils"


export class TextControl extends Control {

    textBox: TextBox
    text = this.getAttribute("text", StringTopic)
    label = this.getAttribute("label", StringTopic)
    editable = this.getAttribute("editable", IntTopic)
    placeholder = this.getAttribute("placeholder", StringTopic)

    protected template = `
    <div class="control flex-horiz">
        <div class="label" id="label">Text</div>
    </div>
    `

    protected css: string = `
        .label{
            flex-shrink: 0;
            min-width: 20px;
        }
    `



    protected onStart(): void {
        super.onStart()
        this.textBox = new TextBox(this.htmlItem.getElByClass("control"),this.editable.getValue()==0)
        // Line height is 17px. The control should be 15+17(n-1)px tall, where n is the number of lines.
        this.textBox.heightDelta = -2
        if(this.editable.getValue()==0){
            (this.htmlItem.baseElement as HTMLDivElement).style.minHeight = "0px"
        }
        this.textBox.textarea.classList.add("control-text","text-field")
        this.textBox.value = this.text.getValue()
        this.textBox.onResize.add(()=>{this.node.moved.invoke()})

        new BindInputBoxAndTopic(this,this.textBox, this.text,this.objectsync,true)

        this.link2(this.textBox as any, "blur", () => {
            this.makeRequest('finish')
        })

        // this.link2(this.textBox as any, "input", () => {
        //     this.makeRequest('suggestions', {text: this.textBox.value})
        // })

        this.textBox.addEventListener("input", () => {
            if (this.textBox.value.endsWith(".")){
                this.makeRequest('suggestions', {text: this.textBox.value}, handleResponse)
            }
        });

        // this.link2(this.textBox as any, "focus", () => {
        //
        // }

        let labelEl = this.htmlItem.getEl("label", HTMLDivElement)
        this.link(this.label.onSet, (label) => {
            if (label == '') {
                labelEl.style.display = 'none'
                return
            }
            //replace spaces with non-breaking spaces
            label = label.replace(/ /g, "\u00a0")

            labelEl.innerHTML = label
        })

        this.link(this.editable.onSet, (editable) => {
            this.textBox.disabled = !editable
        })

        this.link(this.placeholder.onSet, (placeholder) => {
            this.textBox.placeholder = placeholder
        })
    }

}

interface ResponseItem {
    key: string;
    value: string;
}

function handleResponse(response: ResponseItem[]) {
    console.log('handleResponse', response)
    const resultsContainer = document.getElementById('results-container');
    if (!resultsContainer) return;

    resultsContainer.innerHTML = '';

    response.forEach(item => {
        const div = document.createElement('div');
        div.textContent = `${item.key} ${item.value}`;
        resultsContainer.appendChild(div);
    });
}
