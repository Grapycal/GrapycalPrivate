import { FloatTopic, IntTopic, ListTopic, Topic } from "objectsync-client"
import { Componentable } from "../component/componentable"
import { as } from "../utils"
import { Workspace } from "../sobjects/workspace"
import { inputFinished } from "../ui_utils/interaction"
import { Editor } from "./Editor"

export class MultiSelectEditorItem extends Componentable {

    get template() {
        return `
        <div class="attribute-editor flex-horiz stretch grow">
            <div ref="nameEl" class="name"></div>
            <input ref="input" id="input" type="checkbox" class="input">
        </div>
        `
    }

    get style(): string {
        return super.style + `
        .name{
            min-width: 100px;
        }
    `
    }

    readonly input: HTMLInputElement
    readonly nameEl: HTMLDivElement
    name: string
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
        this.connectedAttributes = connectedAttributes
        this.attributeName.innerText = displayName
        this.options = new Map()

        for(let optionName of editorArgs.options){
            const item = new MultiSelectEditorItem().mount(this.optionsContainer)
            item.nameEl.innerText = optionName
            item.name = optionName
            this.options.set(optionName, item)
            this.linker.link2(item.input, 'change', this.inputChanged)
        }

        for (let attr of connectedAttributes) {
            this.linker.link(attr.onSet, this.updateValue)
        }
    }

    private updateValue() {
        for(let option of this.options.values()){

            let hasFalse = false
            let hasTrue = false
            for(let attr of this.connectedAttributes){
                if(attr.getValue().includes(option.name)){
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
        let checked: string[] = []
        let unchecked: string[] = []

        for(let option of this.options.values()){
            if(option.input.checked){
                checked.push(option.name)
            }
            else if(!option.input.indeterminate){
                unchecked.push(option.name)
            }
        }
        Workspace.instance.record(() => {
            for (let attr of this.connectedAttributes) {
                let value = attr.getValue().slice()
                for(let option of checked){
                    if(!value.includes(option)){
                        value.push(option)
                    }
                }
                for(let option of unchecked){
                    value = value.filter(v => v !== option)
                }
                attr.set(value)
            }
        })
    }
}
