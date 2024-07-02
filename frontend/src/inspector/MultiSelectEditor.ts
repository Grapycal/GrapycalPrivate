import { FloatTopic, IntTopic, ListTopic, Topic } from "objectsync-client"
import { Componentable } from "../component/componentable"
import { as } from "../utils"
import { Workspace } from "../sobjects/workspace"
import { inputFinished } from "../ui_utils/interaction"
import { Editor } from "./Editor"

export class MultiSelectEditorItem extends Componentable {

    get template() {
        return `
        <div class="attribute-editor flex-horiz stretch">
            <div ref="name" ></div>
            <input ref="input" id="input" type="checkbox" class="text-editor">
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
    readonly name: HTMLDivElement
    
}

export class MultiSelectEditor extends Editor<ListTopic<string>> {

    get template() {
        return `
        <div class="attribute-editor flex-horiz stretch">
            <div ref="attributeName" id="attribute-name" class="attribute-name"></div>
            <div ref = "optionsContainer">
            </div>
            
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
    readonly attributeName: HTMLDivElement
    readonly optionsContainer: HTMLDivElement
    private readonly options: Map<string, MultiSelectEditorItem>

    constructor(displayName: string, editorArgs: any, connectedAttributes: ListTopic<string>[]) {
        super()
        this.attributeName.innerText = displayName
        for (let attr of connectedAttributes) {
            this.linker.link(attr.onSet, this.updateValue)
        }
        this.updateValue()

        this.options = new Map()
        for(let optionName of editorArgs.options){
            const item = new MultiSelectEditorItem().mount(this.optionsContainer)
            item.name.innerText = optionName
            this.options.set(optionName, item)
            this.linker.link2(item.input, 'change', this.inputChanged)
        }
    }

    private updateValue() {
        let hasFalse = false
        let hasTrue = false
        for(let option of this.options.values()){
            for(let attr of this.connectedAttributes){
                if(attr.getValue().includes(option.name.innerText)){
                    hasTrue = true
                }else{
                    hasFalse = true
                }
            }
            if(hasTrue && hasFalse){
                option.input.indeterminate = true
                option.input.checked = false
            }else{
                option.input.indeterminate = false
                option.input.checked = hasTrue
            }
        }


    }

    private inputChanged() {
        let value = []
        for(let option of this.options.values()){
            if(option.input.checked){
                value.push(option.name.innerText)
            }
        }
        Workspace.instance.record(() => {
            for (let attr of this.connectedAttributes) {
                attr.set(value)
            }
        })
    }
}
