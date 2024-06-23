import { FloatTopic, GenericTopic, IntTopic, StringTopic } from "objectsync-client"
import { Control } from "./control"

export class FloatControl extends Control{
    protected get template (){return `
    <div class="control flex-horiz">
        <label ref="labelEl"></label>
        <input ref="input"  type="number">
    </div>
    `}

    protected get style(){return`
        .control {
            justify-content: space-between;
        }
        input{
            margin: 0;
        }
    `}

    input: HTMLInputElement
    labelEl: HTMLLabelElement
    label = this.getAttribute("label", StringTopic)
    value = this.getAttribute("value", FloatTopic)

    protected onStart(): void {
        super.onStart()
        this.link(this.value.onSet, (newValue) => {
            this.input.valueAsNumber = newValue
        })
        this.input.onblur = () => {
            this.value.set(parseFloat(this.input.value))
        }
        this.input.onkeydown = (e) => {
            if (e.key == 'Enter') {
                this.value.set(parseFloat(this.input.value))
            }
        }
        this.link(this.label.onSet, (newValue) => {
            this.labelEl.innerText = newValue
        })
    }
}