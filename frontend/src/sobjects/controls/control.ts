import { SObject, Topic } from "objectsync-client"
import { CompSObject } from "../compSObject"
import { HtmlItem } from "../../component/htmlItem"
import { Node } from "../node"
import { Constructor, as } from "../../utils"
import { IControlHost } from "./controlHost"
import { Port } from "../port"
import { CEditor } from "../../ceditor/CEditor"

function asControlHost(object: SObject): IControlHost {
    //ordinary as() can't be used since interface doesn't have a constructor
    //so here we check the properties directly
    let typeErasedObject = object as unknown as IControlHost
    if (typeErasedObject.htmlItem !== undefined && typeErasedObject.ancestorNode !== undefined) {
        return typeErasedObject;
    }   
    if (typeErasedObject === null) {
        return null;
    }
    throw new Error(`Value ${object} is not instance of ControlHost`);
}

export class Control extends CompSObject {
    public get node(): Node {
        return asControlHost(this.parent).ancestorNode;
    }
    protected get template (){return `
    <div class="control">
        this is a control
    </div>
    `}
    
    onParentChangedTo(newParent: SObject): void {
        super.onParentChangedTo(newParent)
        this.htmlItem.setParent(asControlHost(newParent).htmlItem,'control')
    }
}

export abstract class ControlWithCEditor extends Control {
    public abstract get valueTopic(): Topic<any>
    public abstract get ceditorType(): Constructor<CEditor>
    public abstract get ceditorArgs(): Topic<any>[]
}