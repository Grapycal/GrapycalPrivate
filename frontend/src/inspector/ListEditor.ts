import { Action, ListTopic, Topic } from "objectsync-client"
import { Componentable } from "../component/componentable"
import { as } from "../utils"
import { Workspace } from "../sobjects/workspace"
import { print } from "../devUtils"
import { object_equal } from "./inspector"
import { Editor } from "./Editor"

export class ListEditor extends Editor<ListTopic<any>> {

    get template() {
        return `
        <div class="attribute-editor flex-horiz stretch">
            <div ref="attributeName" class="attribute-name"></div>
            <div class="container">
                <div ref="container" class="container" slot="container" id="container"></div>
                <div class="container horiz">
                    <input ref="addInput" type="text" class="grow">
                    <button ref="addButton" class="button center-align">+</button>
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
        .horiz{
            flex-direction: row;
        }
        
        .button{
            height: 20px;
            line-height: 0px;
        }
    `
    }

    private readonly container: HTMLDivElement
    private readonly addButton: HTMLButtonElement
    private readonly addInput: HTMLInputElement
    private readonly attributeName: HTMLDivElement
    private readonly items: Set<ListEditorItem> = new Set();
    private locked = false;


    constructor(displayName: string, editorArgs: any, connectedAttributes: Topic<any>[]) {
        super()
        this.connectedAttributes = []
        for (let attr of connectedAttributes) {
            this.connectedAttributes.push(as(attr, ListTopic))
        }

        this.linker.link2(this.addInput, 'keydown', (e: KeyboardEvent) => {
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

    private updateValue() {
        if (this.locked) return
        let value: any[] = null
        for (let attr of this.connectedAttributes) {
            if (value === null) {
                value = attr.getValue()
            } else {
                if (!object_equal(value, attr.getValue())) {
                    value = null
                    break
                }
            }
        }

        // First destroy all items (Sorry, performance)
        for (let item of this.items.values()) {
            item.destroy()
        }
        this.items.clear()
        
        if (value === null) {
            this.container.innerText = 'multiple values'

        } else {
            this.container.innerText = ''
            let pos = 0
            for (let itemText of value) {
                let itemComponent = new ListEditorItem(itemText, pos++)
                this.linker.link(itemComponent.deleteClicked, this.deleteHandler)
                this.items.add(itemComponent)
                itemComponent.htmlItem.setParent(this.htmlItem, 'container')
            }
        }
    }

    private addHandler() {
        let text = this.addInput.value
        if (text === '') return
        this.addInput.value = ''
        this.locked = true
        Workspace.instance.record(() => {
            for (let attr of this.connectedAttributes) {
                attr.insert(text)
            }
        })
        this.locked = false
        this.updateValue() // Manually update value because it was locked when attribute was changed
    }

    private deleteHandler(item: ListEditorItem) {
        this.locked = true
        Workspace.instance.record(() => {
            for (let attr of this.connectedAttributes) {
                attr.pop(item.position)
            }
        })
        this.items.delete(item)

        this.locked = false
        this.updateValue() // Manually update value because it was locked when attribute was changed
    }
}
class ListEditorItem extends Componentable {

    get template() {
        return `
        <div class="item flex-horiz stretch">
            <div ref="textDiv" class="text"></div>
            <button ref="deleteButton" class="button center-align">-</button>
        </div>
        `
    }

    get style(): string {
        return super.style + `
        .item{
            margin: 2px 0px;
            border: 1px outset #373737;
            flex-grow: 1;
            background-color: #181818;
            min-width: 0px;
        }
        .text{
            flex-grow: 1;
            margin-left: 5px;
            min-width: 0px; /* prevent too large width when overflow*/
            overflow: hidden;
        }
        .button{
            height: 20px;
            line-height: 0px;
        }
   `
    }

    readonly text: string
    readonly position: number

    readonly textDiv: HTMLDivElement
    public readonly deleteButton: HTMLButtonElement

    public readonly deleteClicked = new Action<[ListEditorItem]>();

    constructor(text: string, position: number) {
        super()
        this.text = text
        this.position = position
        this.textDiv.innerText = text
        this.linker.link2(this.deleteButton, 'click', this.deleteClickedHandler)
    }

    private deleteClickedHandler() {
        this.destroy()
        this.deleteClicked.invoke(this)
    }
}
