import { GenericTopic, IntTopic, Topic } from "objectsync-client"
import { as } from "../utils"
import { Workspace } from "../sobjects/workspace"
import { inputFinished } from "../ui_utils/interaction"
import { Editor } from "./Editor"

export class ToggleEditor extends Editor<GenericTopic<boolean>> {

    get template() {
        return `
        <div class="attribute-editor flex-horiz stretch">
            <div ref="attributeName" id="attribute-name" class="attribute-name"></div>
            <input ref="input" id="input" type="checkbox" class="text-editor">
        </div>
        `
    }

    get style(): string {
        return super.style + `
    `
    }

    readonly input: HTMLInputElement
    readonly attributeName: HTMLDivElement
    private locked = false;

    constructor(displayName: string, editorArgs: any, connectedAttributes: Topic<any>[]) {
        super()
        this.connectedAttributes = connectedAttributes as GenericTopic<boolean>[]
        this.attributeName.innerText = displayName
        for (let attr of connectedAttributes) {
            attr = as(attr, GenericTopic<boolean>)
            this.linker.link(attr.onSet, this.updateValue)
        }
        this.linker.link(inputFinished(this.input),this.inputFinished)
        this.updateValue()
    }

    private updateValue() {
        if (this.locked) return
        let value: boolean = null
        for (let attr of this.connectedAttributes) {
            if (value === null) {
                value = attr.getValue()
            } else {
                if (value !== attr.getValue()) {
                    value = null
                    break
                }
            }
        }
        if (value === null) {
            this.input.value = ''
            this.input.placeholder = 'multiple values'
        } else {
            this.input.checked = value
        }
    }

    private inputFinished() {
        this.locked = true
        Workspace.instance.record(() => {
            for (let attr of this.connectedAttributes) {
                attr = as(attr, GenericTopic<boolean>)
                attr.set(this.input.checked)
            }
        })
        this.locked = false
    }
}
