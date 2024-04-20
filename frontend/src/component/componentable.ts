import { EventDispatcher } from "./eventDispatcher"
import { HtmlItem } from "./htmlItem"
import { Linker } from "./linker"
import { IComponentable, ComponentManager } from "./component"
import { print } from "../devUtils"
import { MouseOverDetector } from "./mouseOverDetector"
import { Selectable } from "./selectable"
import { Transform } from "./transform"


export class Componentable implements IComponentable {
    // This class has the common components by default, providing a convenient starting point for defining an IComponentable class.

    readonly componentManager = new ComponentManager()
    // The default value is an empty div because HtmlItem requires at least one element in the template.
    private _htmlItem: HtmlItem = null;
    protected get template(): string { return '<div></div>' }
    protected get style(): string { return '' }
    get htmlItem(): HtmlItem {
        if (this._htmlItem == null) {
            this._htmlItem = new HtmlItem(this, null, this.template, this.style);
            // iterate through all refs and assign them to this
            for (let [name,el] of this._htmlItem.getRefs()) {
                (this as any)[name] = el;
            }
        }
        return this._htmlItem;
    }

    private _transform: Transform = null;
    get transform(): Transform {
        if (this._transform == null) {
            this.htmlItem; // Ensure htmlItem is created
            this.eventDispatcher; // Ensure eventDispatcher is created
            this._transform = new Transform(this);
        }
        return this._transform;
    }

    private _eventDispatcher: EventDispatcher = null;
    get eventDispatcher(): EventDispatcher {
        if (this._eventDispatcher == null) {
            this._eventDispatcher = new EventDispatcher(this);
        }
        return this._eventDispatcher;
    }

    private _selectable: Selectable = null;
    get selectable(): Selectable {
        this.eventDispatcher; // Ensure eventDispatcher is created
        if (this._selectable == null) {
            this._selectable = new Selectable(this);
        }
        return this._selectable;
    }

    private _mouseOverDetector: MouseOverDetector = null;
    get mouseOverDetector(): MouseOverDetector {
        if (this._mouseOverDetector == null) {
            this.eventDispatcher; // Ensure eventDispatcher is created
            this._mouseOverDetector = new MouseOverDetector(this);
        }
        return this._mouseOverDetector;
    }
    protected readonly linker: Linker
    protected readonly link
    protected readonly link2
    protected readonly unlink
    protected readonly unlink2

    constructor() {
        if(this.template != `<div></div>`)
            this.htmlItem; // Create the htmlItem prior to other components to prevent errors
        
        this.linker = new Linker(this)
        this.link = this.linker.link.bind(this.linker)
        this.link2 = this.linker.link2.bind(this.linker)
        this.unlink = this.linker.unlink.bind(this.linker)
        this.unlink2 = this.linker.unlink2.bind(this.linker)

        this.componentManager.onDestroy.add(this.onDestroy.bind(this))
    }

    mount(parent: IComponentable|HtmlItem|HTMLElement, slot: string = null): this {
        if (parent instanceof HTMLElement) {
            this.htmlItem.setParentElement(parent)
            return this
        }
        let parent_: HtmlItem
        if (parent instanceof HtmlItem) {
            parent_ = parent
        }
        else {
            parent_ = parent.componentManager.getComponent(HtmlItem)
        }
        if(slot === null){
            slot = this.constructor.name
        }
        this.htmlItem.setParent(parent_, slot)
        return this
    }

    /**
     * Call this method to destroy the componentable. Its components will do cleanup.
     * This method should be called when the componentable is no longer needed.
    */
    destroy(): void {
        this.componentManager.destroy()
    }

    /**
    * Called when the componetable is destroyed. Override this method to clean up any resources.
    */
    onDestroy(): void {
    }

}
