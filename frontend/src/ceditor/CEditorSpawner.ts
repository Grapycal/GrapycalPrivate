import { HtmlItem } from "../component/htmlItem"
import { Control, ControlWithCEditor } from "../sobjects/controls/control"
import { Constructor, TopicBus } from "../utils"
import { CEditor } from "./CEditor"

export class CEditorSpawner{
    private currentCEditor:CEditor
    constructor(private controls:ControlWithCEditor[], private mount:HtmlItem){
        
    }

    spawn(){
        if (this.currentCEditor){
            this.currentCEditor.destroy()
        }
        let objectsync = this.controls[0].objectsync
        this.currentCEditor = new this.controls[0].ceditorType(
            objectsync,
            new TopicBus(this.controls.map(control => control.valueTopic)),
            this.attributeNames
        )
        this.currentCEditor.mount(this.mount)
    }
        

}