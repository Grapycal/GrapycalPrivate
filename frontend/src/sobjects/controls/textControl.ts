import { EventTopic, IntTopic, StringTopic } from "objectsync-client"
import { Control } from "./control"
import { print } from "../../devUtils"
import { BindInputBoxAndTopic } from "../../ui_utils/interaction"
import { TextBox} from "../../utils"
import { TextCEditor } from "../../ceditor/TextCEditor"


export class TextControl extends Control {

    textBox: TextBox
    text = this.getAttribute("text", StringTopic)
    label = this.getAttribute("label", StringTopic)
    editable = this.getAttribute("editable", IntTopic)
    placeholder = this.getAttribute("placeholder", StringTopic)

    protected get template (){return `
    <div slot="editor">
    </div>
    `}

    protected onStart(): void {
        super.onStart()
        new TextCEditor(this.objectsync, [this.text], this.label.getValue(), this.editable.getValue(), this.placeholder.getValue(), 0
        ).mount(this, "editor")
    }
}
