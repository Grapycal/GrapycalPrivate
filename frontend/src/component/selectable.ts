import { print } from "../devUtils"
import { Action } from "../utils"
import { Component, IComponentable } from "./component"
import { EventDispatcher } from "./eventDispatcher"
import { SelectionManager } from "./selectionManager"

export class Selectable extends Component{
    private _selectionManager: SelectionManager
    set selectionManager(value: SelectionManager){
        if(this._selectionManager != null) this._selectionManager.unregister(this)
        this._selectionManager = value
        if(value != null)
            value.register(this)
    }
    get selectionManager(): SelectionManager{
        return this._selectionManager
    }
    onSelected: Action<[]> = new Action()
    onDeselected: Action<[]> = new Action()

    private _selected: boolean = false
    get selected(): boolean{
        return this._selected
    }

    private _enabled: boolean = true
    get enabled(): boolean{
        return this._enabled
    }
    set enabled(value: boolean){
        if(!value && this._selected) this.deselect()
        this._enabled = value
    }

    get selectedObjects(): Set<Selectable>{
        return this.selectionManager.selected
    }

    constructor(object: IComponentable, selectionManager:SelectionManager=null){
        super(object)
        if(selectionManager != null){
            this.selectionManager = selectionManager
        }
        this.getComponent(EventDispatcher).onClick.add(this.click.bind(this))
    }

    onDestroy(){
        if (this.selectionManager != null)
            this.selectionManager.unregister(this)
    }

    click(){
        // Let selection manager handle the click
        if(!this.enabled) return;
        this.selectionManager.click(this)
    }

    /* Called by selectionManager */
    select_raw(){
        if(this._selected) return;
        this._selected = true;
        this.onSelected.invoke()
    }

    deselect_raw(){
        if(!this._selected) return;
        this._selected = false;
        this.onDeselected.invoke()
    }

    /* Shortcut methods */

    select(){
        this.selectionManager.select(this)
    }

    deselect(){
        this.selectionManager.deselect(this)
    }


}