import { EventTopic, IntTopic, StringTopic } from "objectsync-client"
import { Control } from "./control"
import { print } from "../../devUtils"
import { BindInputBoxAndTopic } from "../../ui_utils/interaction"
import { TextBox} from "../../utils"


export class ObjectControl extends Control {

    textBox: TextBox
    text = this.getAttribute("text", StringTopic)
    label = this.getAttribute("label", StringTopic)

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



    protected onStart(): void {
        super.onStart()
        this.textBox = new TextBox(this.htmlItem.getElByClass("control"))
        // Line height is 17px. The control should be 15+17(n-1)px tall, where n is the number of lines.
        this.textBox.heightDelta = -2
        this.textBox.textarea.classList.add("control-text","text-field")
        this.textBox.value = this.text.getValue()
        this.textBox.onResize.add(()=>{this.node.moved.invoke()})

        new BindInputBoxAndTopic(this,this.textBox, this.text,this.objectsync,false)

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

        // this.textBox.disabled = true
    }

}
