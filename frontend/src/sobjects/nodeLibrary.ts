import { CompSObject } from './compSObject'
import { HtmlItem } from '../component/htmlItem'
import { HierarchyNode } from '../ui_utils/hierarchyNode'
import { as } from '../utils'
import { print } from '../devUtils'
import { ExtensionsSetting } from '../ui_utils/extensionsSettings'
import { Workspace } from './workspace'

export class NodeLibrary extends CompSObject {
    /**
    * The left sidebar is a tabbed interface with the following tabs:
    * - File View
    * - Node List
    * - Extensions
    * - Settings
    * - Examples
    * - About
    */

    private items: HtmlItem[] = []
    nodeLibrary: HierarchyNode = new HierarchyNode('', '',true);
    tabs = new Map<HTMLButtonElement, HTMLDivElement>();
    sidebarContainer: HTMLDivElement;
    onStart() {
        this.mount(Workspace.instance)
        new ExtensionsSetting(this.objectsync);
        this.nodeLibrary.htmlItem.setParentElement(Workspace.instance.leftSidebar.htmlItem.getSlot('NodeLibrary'))
    }

    addItem(htmlItem: HtmlItem, path: string) {
        this.nodeLibrary.addLeaf(htmlItem, path)
        this.items.push(htmlItem)
    }

    hasItem(htmlItem: HtmlItem) {
        return this.items.includes(htmlItem)
    }

    removeItem(htmlItem: HtmlItem, path: string) {
        this.nodeLibrary.removeLeaf(htmlItem, path)
        this.items.splice(this.items.indexOf(htmlItem), 1)
    }
    
}