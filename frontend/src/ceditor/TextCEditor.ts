import { Action, EventTopic, IntTopic, ObjectSyncClient, StringTopic, Topic } from "objectsync-client"

import { BindInputBoxAndTopic } from "../ui_utils/interaction"
import { TextBox} from "../utils"
import { Componentable } from "../component/componentable"
import { Control } from "../sobjects/controls/control"
import { TextControl } from "../sobjects/controls/textControl"
import { CEditor } from "./CEditor"

enum UpdateMode {
    CHANGE = 0,
    FINISH = 1,
}

    
export class TextCEditor extends CEditor {

    textBox: TextBox

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

    constructor(objectsync:ObjectSyncClient, topics: StringTopic[], label:string, editable:number, placeholder:string, updateMode:number){
        super()

        this.textBox = new TextBox(this.htmlItem.getElByClass("control"),editable==0)
        // Line height is 17px. The control should be 15+17(n-1)px tall, where n is the number of lines.
        this.textBox.heightDelta = -2
        if(editable==0){
            (this.htmlItem.baseElement as HTMLDivElement).style.minHeight = "0px"
        }
        this.textBox.textarea.classList.add("control-text","text-field")
        //this.textBox.value = this.text.getValue()
        this.textBox.onResize.add(this.onResize.invoke)

        let bindInputBox = new BindInputBoxAndTopic(
            this,
            this.textBox, 
            topics,
            objectsync,
            updateMode == UpdateMode.CHANGE
        )

        let labelEl = this.htmlItem.getEl("label", HTMLDivElement)
        if (label == '') {
            labelEl.style.display = 'none'
            return
        }
        //replace spaces with non-breaking spaces
        label = label.replace(/ /g, "\u00a0")

        labelEl.innerHTML = label
        
        this.textBox.disabled = !editable       
        this.textBox.placeholder = placeholder
    }

}
