import { Action, DictTopic, ListTopic, Topic } from "objectsync-client"
import { Componentable } from "../component/componentable"
import { as } from "../utils"
import { Workspace } from "../sobjects/workspace"
import { print } from "../devUtils"
import { object_equal } from "./inspector"
import { Editor } from "./Editor"
import { AutoCompMenu } from "../ui_utils/popupMenu/autoCompMenu"

type DictEditorArgs = {
    key_options?: string[]
    key_strict?: boolean
    value_options?: string[]
    value_strict?: boolean
}

export class DictEditor extends Editor<DictTopic<string,string>> {

    get template() {
        return `
        <div class="attribute-editor flex-horiz stretch">
            <div ref="attributeName" id="attribute-name" class="attribute-name"></div>
            <div ref="container" class="container">
                <div class="container" slot="container" id="container"></div>
                <div class="container container2">
                    <div slot="key" class="grow"></div>
                    <span id="colon">:</span>
                    <div slot="value" class="grow"></div>
                    <button ref="addButton" id="add-button" class="button center-align">+</button>
                </div>
            </div>
        </div>
    `
    }

    get style(): string {
        return super.style + `
        .container{
            display: flex;
            flex-direction: column;
            align-items: stretch;
            flex-grow: 1;
            margin: 4px 10px;
            min-width: 0px;
        }
        .container2{
            height: 20px;
            align-items: baseline;
            flex-direction: row;
            display: flex;
        }
        .horiz{
        }
        
        .button{
            height: 20px;
            line-height: 0px;
        }
        #colon{
            margin: 0px 5px;
        }
    `
    }

    private readonly container: HTMLDivElement
    private readonly addButton: HTMLButtonElement
    private readonly attributeName: HTMLDivElement

    private readonly keyInput: AutoCompMenu
    private readonly valueInput: AutoCompMenu
    private readonly items: Set<DictEditorItem> = new Set();
    private locked = false;
    private readonly allowedKeys: string[]|null = null

    constructor(displayName: string, private editorArgs: DictEditorArgs, connectedAttributes:DictTopic<string,string>[]) {
        super()
        this.connectedAttributes = connectedAttributes

        this.keyInput = new AutoCompMenu()
        this.valueInput = new AutoCompMenu()
        this.keyInput.htmlItem.setParent(this.htmlItem, 'key')
        this.keyInput.open()
        if(editorArgs.key_options){
            this.keyInput.setOptions(editorArgs.key_options.map((key)=>{
                return {key:key,value:key,callback:()=>{}}
            }))
        }
        this.valueInput.htmlItem.setParent(this.htmlItem, 'value')
        this.valueInput.open()
        if(editorArgs.value_options){
            this.valueInput.setOptions(editorArgs.value_options.map((value)=>{
                return {key:value,value:value,callback:()=>{}}
            }))
        }

        this.link2(this.htmlItem.baseElement, 'keydown', (e: KeyboardEvent) => {
            if (e.key === 'Enter') {
                this.addHandler()
            }
        })

        this.linker.link2(this.addButton, 'click', this.addHandler)

        this.attributeName.innerText = displayName

        for (let attr of connectedAttributes) {
            this.linker.link(attr.onSet, this.updateValue)
        }

        this.updateValue()
    }

    private getCommonKeyValue(maps: Map<string,string>[]): [string,string|null][]{
        let res: [string,string|null][] = []
        if (maps.length === 0) return res
        let firstMap = maps[0]
        for(let key of firstMap.keys()){
            let isCommon = true
            for(let map of maps){
                if(!map.has(key)){
                    isCommon = false
                    break
                }
            }
            if(isCommon){
                let commonValue = firstMap.get(key)!
                for(let map of maps){
                    if(map.get(key) !== firstMap.get(key)){
                        commonValue = null
                        break
                    }
                }
                res.push([key,commonValue])
            }
        }
        return res
    }

    private updateValue() {
        if (this.locked) return
        
        let maps: Map<string,string>[] = []
        for (let attr of this.connectedAttributes) {
            maps.push(attr.getValue())
        }
        let commonKeys = this.getCommonKeyValue(maps)

        // First destroy all items (Sorry, performance)
        for (let item of this.items.values()) {
            item.destroy()
        }
        this.items.clear()
        
        this.container.innerText = ''
        for (let [key,value] of commonKeys) {
            let itemComponent = new DictEditorItem(key, value)
            this.link(itemComponent.valueChanged, this.valueChangedHandler)
            this.link(itemComponent.deleteClicked, this.deleteHandler)
            this.items.add(itemComponent)
            itemComponent.htmlItem.setParent(this.htmlItem, 'container')
        }
        
        // Take away existing keys from key options
        let keyOptions = this.editorArgs.key_options.slice() // copy
        for(let [key,value] of commonKeys){
            let index = keyOptions.indexOf(key)
            if(index !== -1){
                keyOptions.splice(index,1)
            }
        }
        this.keyInput.setOptions(keyOptions.map((key)=>{
            return {key:key,value:key,callback:()=>{}}
        }))

    }
        

    private addHandler() {
        let key = this.keyInput.value
        let value = this.valueInput.value
        if(this.editorArgs.key_strict && !this.editorArgs.key_options!.includes(key))
            return
        if(this.editorArgs.value_strict && !this.editorArgs.value_options!.includes(value))
            return

        this.keyInput.value = ''
        this.valueInput.value = ''
        this.locked = true
            
        try{
            Workspace.instance.record(() => {
                for (let attr of this.connectedAttributes) {
                    attr.add(key,value)
                }
            })
        }catch(e){
            console.warn(e)
            return
        }
        this.locked = false
        this.updateValue() // Manually update value because it was locked when attribute was changed
    }

    private valueChangedHandler(key:string, value: string) {
        this.locked = true
        Workspace.instance.record(() => {
            for (let attr of this.connectedAttributes) {
                attr.changeValue(key,value)
            }
        })
        this.locked = false
    }

    private deleteHandler(item: DictEditorItem) {
        this.locked = true
        Workspace.instance.record(() => {
            for (let attr of this.connectedAttributes) {
                attr.pop(item.key)
            }
        })
        this.items.delete(item)

        this.locked = false
        this.updateValue() // Manually update value because it was locked when attribute was changed
    }
}
class DictEditorItem extends Componentable {

    get template() {
        return `
        <div class="item flex-horiz stretch">
            <div id="keyDiv"class="text grow"></div>
            <input id="valueInput" type="text" class="grow">
            <button id="deleteButton" class="button center-align">-</button>
        </div>
        `
    }

    get style(): string {
        return super.style + `
        .item{
            margin: 2px 0px;
            border: 1px outset #373737;
            flex-grow: 1;
            background-color: var(--z2);
            min-width: 0px;
        }
        .text{
            flex-grow: 1;
            margin-left: 5px;
            min-width: 30px; /* prevent too large width when overflow*/
            overflow: hidden;
        }
        #dict-editor-item-value{
            border: gray 1px solid;
        }
        .button{
            height: 20px;
            line-height: 0px;
        }
   `
    }

    /* Element References */


    private readonly keyDiv: HTMLDivElement
    private readonly valueInput: HTMLInputElement
    private readonly deleteButton: HTMLButtonElement

    /* Other Variables */

    readonly key: string
    public readonly valueChanged = new Action<[string,string]>();
    public readonly deleteClicked = new Action<[DictEditorItem]>();

    private locked = false

    constructor(key: string,value: string) {
        super()
        this.key = key
        
        this.keyDiv.innerText = key
        if(value === null){
            this.valueInput.placeholder = 'Multiple values'
        }else{
            this.valueInput.value = value
        }
        this.link2(this.valueInput, 'input', this.valueChangedHandler)
        this.link2(this.deleteButton, 'click', this.deleteClickedHandler)
    }

    public changeValue(value: string) {
        this.locked = true
        this.valueInput.value = value
        this.locked = false
    }

    private valueChangedHandler() {
        if (this.locked) return
        this.valueChanged.invoke(this.key,this.valueInput.value)
    }

    private deleteClickedHandler() {
        this.destroy()
        this.deleteClicked.invoke(this)
    }
}
