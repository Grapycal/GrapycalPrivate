import { ObjectSyncClient, SObject } from "objectsync-client"
import { Component, ComponentManager, IComponentable } from "../component/component"
import { Constructor, as } from "../utils"
import { HtmlItem } from "../component/htmlItem"
import { Transform } from "../component/transform"
import { EventDispatcher } from "../component/eventDispatcher"
import { Linker } from "../component/linker"
import { Selectable } from "../component/selectable"
import { MouseOverDetector } from "../component/mouseOverDetector"

export class CompSObject extends SObject implements IComponentable {

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

    private _linker: Linker = null;
    get linker(): Linker {
        if (this._linker == null) {
            this._linker = new Linker(this);
        }
        return this._linker;
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

    componentManager: ComponentManager = new ComponentManager();
    constructor(objectsync: ObjectSyncClient, id: string) {
        super(objectsync, id);
        if(this.template != `<div></div>`)
            this.htmlItem; // Create the htmlItem prior to other components to prevent errors
    }

    public get parent(): CompSObject {
        if (super.parent == null)
            return null;
        return as(super.parent, CompSObject);
    }

    public getComponentInAncestorsOrThis<T extends Component>(type: Constructor<T>): T | null {
        if (this.hasComponent(type))
            return this.getComponent(type);
        else if (this.isRoot)
            return null;
        else
            return this.parent.getComponentInAncestorsOrThis(type);
    }
    getComponentInAncestors<T extends Component>(type: Constructor<T>): T | null {
        if (this.isRoot)
            return null;
        return this.parent.getComponentInAncestorsOrThis(type);
    }

    public getComponent<T extends Component>(type: Constructor<T>): T {
        return this.componentManager.getComponent(type);
    }
    public hasComponent<T extends Component>(type: Constructor<T>): boolean {
        return this.componentManager.hasComponent(type);
    }
    public onDestroy(): void {
        super.onDestroy();
        this.componentManager.destroy();
    }
}