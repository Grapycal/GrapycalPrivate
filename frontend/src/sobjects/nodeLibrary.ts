import { CompSObject } from './compSObject'
import { HtmlItem } from '../component/htmlItem'
import { HierarchyNode } from '../ui_utils/hierarchyNode'
import { as } from '../utils'
import { print } from '../devUtils'
import { ExtensionsSetting } from '../ui_utils/extensionsSettings'
import { Workspace } from './workspace'

export class NodeLibrary extends CompSObject {
    protected get template(): string {return`
    <div>
        <div class="sidebar-tab-title">
        <h1>Node Library</h1>
        <hr>
        </div>
        Want more nodes? Extend the list at 🚀Extensions tab.
        <br></br>
        <div slot="HierarchyNode"></div>
    </div>
    `}

    private items: HtmlItem[] = []
    hierarchy: HierarchyNode = new HierarchyNode('', '',true);
    tabs = new Map<HTMLButtonElement, HTMLDivElement>();
    sidebarContainer: HTMLDivElement;
    onStart() {
        this.mount(Workspace.instance.leftSidebar)
        this.hierarchy.mount(this)
    }

    addItem(htmlItem: HtmlItem, path: string) {
        this.hierarchy.addLeaf(htmlItem, path)
        this.items.push(htmlItem)
    }

    hasItem(htmlItem: HtmlItem) {
        return this.items.includes(htmlItem)
    }

    removeItem(htmlItem: HtmlItem, path: string) {
        this.hierarchy.removeLeaf(htmlItem, path)
        this.items.splice(this.items.indexOf(htmlItem), 1)
    }
    
}