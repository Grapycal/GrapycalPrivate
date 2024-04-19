import { EventTopic, Topic } from "objectsync-client"
import { as } from "../utils"
import { Editor } from "./Editor"

export class ButtonEditor extends Editor<EventTopic> {

    get template() {
        return `
        <div class="attribute-editor flex-horiz stretch">
            <button ref="button" id="btn" type="button" class="btn grow"></button>
        </div>
        `
    }
    readonly button: HTMLButtonElement

    constructor(displayName: string, editorArgs: any, connectedAttributes: Topic<any>[]) {
        super()
        //this.connectedAttributes = connectedAttributes
        for(let attr of connectedAttributes){
            this.connectedAttributes.push(as(attr,EventTopic))
        }
        this.button.innerText = displayName
        this.linker.link2(this.button, 'click', this.buttonClicked)
    }

    private buttonClicked() {
        for(let attr of this.connectedAttributes){
            attr.emit()
        }
    }

}
