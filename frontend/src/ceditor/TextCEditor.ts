import { EventTopic, IntTopic, StringTopic } from "objectsync-client"

import { BindInputBoxAndTopic } from "../ui_utils/interaction"
import { TextBox} from "../utils"
import { Componentable } from "../component/componentable"
import { Control } from "../sobjects/controls/control"


export class TextCEditor extends Componentable {

    textBox: TextBox
    control: Control

    protected get template (){return `
    <div class="control flex-horiz">
        <div class="label" id="label">Text</div>
    </div>
    `}

    protected css: string = `
        .label{
            flex-shrink: 0;
            min-width: 20px;
        }
    `

    text: StringTopic
    label: StringTopic
    editable: IntTopic
    placeholder: StringTopic

    constructor(control:Control) {
        super()
        this.control = control
        this.text = this.control.getAttribute("text", StringTopic)
        this.label = this.control.getAttribute("label", StringTopic)
        this.editable = this.control.getAttribute("editable", IntTopic)
        this.placeholder = this.control.getAttribute("placeholder", StringTopic)

        this.textBox = new TextBox(this.htmlItem.getElByClass("control"),this.editable.getValue()==0)
        // Line height is 17px. The control should be 15+17(n-1)px tall, where n is the number of lines.
        this.textBox.heightDelta = -2
        if(this.editable.getValue()==0){
            (this.htmlItem.baseElement as HTMLDivElement).style.minHeight = "0px"
        }
        this.textBox.textarea.classList.add("control-text","text-field")
        this.textBox.value = this.text.getValue()
        this.textBox.onResize.add(()=>{this.control.node.moved.invoke()})

        new BindInputBoxAndTopic(this,this.textBox, this.text,this.objectsync,true)

        this.link2(this.textBox as any, "blur", () => {
            this.control.makeRequest('finish')
        })

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
