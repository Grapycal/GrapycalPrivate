import { GenericTopic, StringTopic } from "objectsync-client"
import { Control } from "./control"

export class ToggleControl extends Control{
    protected get template (){return `
    <div class="control flex-horiz">
        <label ref="labelEl"></label>
        <input ref="input" type="checkbox">
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
    value = this.getAttribute("value", GenericTopic<boolean>)

    protected onStart(): void {
        super.onStart()
        this.link(this.value.onSet, (newValue) => {
            this.input.checked = newValue
        })
        this.input.oninput = () => {
            this.value.set(this.input.checked)
        }
        this.link(this.label.onSet, (newValue) => {
            this.labelEl.innerText = newValue
        })
    }
}