import { StringTopic } from "objectsync-client"
import { ComponentManager, IComponentable } from "../component/component"
import { Workspace } from "../sobjects/workspace"
import { BindInputBoxAndTopic, inputFinished } from "../ui_utils/interaction"
import { Editor } from "./Editor"

export class TextEditor extends Editor<StringTopic> {

    protected get template(): string { return `
    <div class="attribute-editor flex-horiz stretch">
        <div ref="attributeName" class="attribute-name"></div>
        <input ref="input" type="text" class="text-editor"></input>
    </div>
    `;
    }
    
    readonly input: HTMLTextAreaElement|HTMLInputElement
    readonly connectedAttributes: StringTopic[]

    private readonly attributeName: HTMLDivElement

    constructor(displayName: string, editorArgs: any, connectedAttributes: StringTopic[]) {
        super()
        this.connectedAttributes = connectedAttributes
        this.attributeName.innerText = displayName
        new BindInputBoxAndTopic(this,this.input, this.connectedAttributes,Workspace.instance.objectsync)
    }

}
