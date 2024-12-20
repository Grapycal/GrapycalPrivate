import { FloatTopic, StringTopic, Topic } from "objectsync-client"
import { Componentable } from "../component/componentable"
import { as } from "../utils"
import { Workspace } from "../sobjects/workspace"
import { inputFinished } from "../ui_utils/interaction"
import { Editor } from "./Editor"

export class OptionsEditor extends Editor<StringTopic> {

    get template() {
        return `
        <div class="attribute-editor flex-horiz stretch">
            <div ref="attributeName" class="attribute-name"></div>
            <select ref="selectInput" class="select">
            </select>
        </div>
        `
    }

    get style(): string {
        return super.style + `
        .select{
            flex-grow: 1;
        }
        .attribute-editor{
            gap: 5px;
        }
    `
    }

    readonly selectInput: HTMLSelectElement
    readonly connectedAttributes: StringTopic[] = []
    private locked = false;

    readonly attributeName: HTMLDivElement

    constructor(displayName: string, editorArgs: any, connectedAttributes: Topic<any>[]|null=null) {
        super()
        if (connectedAttributes === null) {
            connectedAttributes = [new StringTopic()]
        }
        for (let attr of connectedAttributes) {
            this.connectedAttributes.push(as(attr, StringTopic))
        }
        for(let option of editorArgs.options){
            const optionEl = document.createElement('option')
            optionEl.value = option
            optionEl.innerText = option
            this.selectInput.appendChild(optionEl)
        }
        this.attributeName.innerText = displayName
        for (let attr of connectedAttributes) {
            attr = as(attr, StringTopic)
            this.linker.link(attr.onSet, this.updateValue)
        }
        this.updateValue()
        this.link2(this.selectInput,'change',this.onSelectChange)
    }

    private updateValue() {
        if (this.locked) return
        let value: string = null
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
            this.selectInput.value = ''
        } else {
            this.selectInput.value = value.toString()
        }
    }

    private onSelectChange() {
        this.locked = true
        Workspace.instance.record(() => {
            for (let attr of this.connectedAttributes) {
                attr.set(this.selectInput.value)
            }
        })
        this.locked = false
    }

    setOptions(options: string[]){
        const value = this.selectInput.value
        this.selectInput.innerHTML = ''
        for (let option of options) {
            const optionEl = document.createElement('option')
            optionEl.value = option
            optionEl.innerText = option
            this.selectInput.appendChild(optionEl)
        }
        if(options.includes(value)){
            this.selectInput.value = value
        }
    }
}
