import { FloatTopic, Topic } from "objectsync-client"
import { Componentable } from "../component/componentable"
import { as } from "../utils"
import { Workspace } from "../sobjects/workspace"
import { inputFinished } from "../ui_utils/interaction"
import { Editor } from "./Editor"

export class FloatEditor extends Editor<FloatTopic> {

    get template() {
        return `
        <div class="attribute-editor flex-horiz stretch">
            <div ref="attributeName" id="attribute-name" class="attribute-name"></div>
            <input ref="input" id="input" type="number" class="text-editor">
        </div>
        `
    }

    get style(): string {
        return super.style + `
        .text-editor{
            width: 100px;
        }
    `
    }

    readonly input: HTMLInputElement
    private locked = false;

    private readonly attributeName: HTMLDivElement

    constructor(displayName: string, editorArgs: any, connectedAttributes: Topic<any>[]) {
        super()
        this.connectedAttributes = connectedAttributes as FloatTopic[]
        this.attributeName.innerText = displayName
        for (let attr of connectedAttributes) {
            attr = as(attr, FloatTopic)
            this.linker.link(attr.onSet, this.updateValue)
        }
        this.linker.link(inputFinished(this.input),this.inputFinished)
        this.updateValue()
    }

    private updateValue() {
        if (this.locked) return
        let value: number = null
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
            this.input.value = value.toString()
        }
    }

    private inputFinished() {
        this.locked = true
        Workspace.instance.record(() => {
            for (let attr of this.connectedAttributes) {
                attr = as(attr, FloatTopic)
                attr.set(Number.parseFloat(this.input.value))
            }
        })
        this.locked = false
    }
}
