import {ObjectSyncClient, StringTopic, IntTopic} from 'objectsync-client'
import { HtmlItem } from '../component/htmlItem'
import { Transform } from '../component/transform'
import { CompSObject } from './compSObject'
import { Node } from './node'
import { print } from '../devUtils'
import { Action, Vector2, as } from '../utils'
import { MouseOverDetector } from '../component/mouseOverDetector'
import { EventDispatcher } from '../component/eventDispatcher'
import { Edge } from './edge'
import { IControlHost } from './controls/controlHost'

export class Port extends CompSObject implements IControlHost {

    display_name: StringTopic = this.getAttribute('display_name', StringTopic)
    is_input: IntTopic = this.getAttribute('is_input', IntTopic)
    max_edges: IntTopic = this.getAttribute('max_edges', IntTopic)
    default_control_display: string
    orientation: number=0;

    // This will be set to true if the type is incompatible during the edge creation period
    // Otherwise, it will be set to false, including those time when the port is not being connected
    _type_incompatible: boolean = false;
    get type_incompatible(): boolean {
        return this._type_incompatible
    }
    set type_incompatible(value: boolean) {
        this._type_incompatible = value
        this.updateAcceptsEdgeClass()
    }

    private node: Node = null;
    
    element = document.createElement('div')

    get ancestorNode(): Node {
        return this.node;
    }

    moved: Action<[]> = new Action();

    set displayLabel(value: boolean) {
        if (value) {
            this.labelDiv.style.display = 'block'
        } else {
            this.labelDiv.style.display = 'none'
        }
    }

    // Called by Edge class
    private edges: Edge[] = []
    addEdge(edge: Edge): void {
        this.edges.push(edge)
        this.htmlItem.baseElement.classList.add('has-edge')
        this.updateAcceptsEdgeClass()
    }
    removeEdge(edge: Edge): void {
        this.edges.splice(this.edges.indexOf(edge), 1)
        if(this.edges.length === 0){
            this.htmlItem.baseElement.classList.remove('has-edge')
        }
        this.updateAcceptsEdgeClass()
    }

    protected get template(): string { return `
    <div class="port">

        <div ref="labelDiv" class="port-label" ></div>
        <div class="slot-control" slot="control"></div>
        <div ref="knob" class="port-knob" id="Knob">
            <div ref="hitbox" class="port-knob-hitbox" id="Hitbox"></div>
        </div>

    </div>
    `}

    knob: HTMLDivElement
    hitbox: HTMLDivElement
    labelDiv: HTMLDivElement

    protected onStart(): void {
        super.onStart()
        this.transform.targetElement = this.knob
        this.transform.pivot = new Vector2(0,0)

        this.eventDispatcher.setEventElement(this.hitbox)
        this.link(this.eventDispatcher.onDragStart,this.generateEdge)

        this.mouseOverDetector.eventElement = this.hitbox

        this.displayLabel = true
        
        // Initializing classes like this prevents UI from glitching (hopefully)
        this.htmlItem.baseElement.classList.add('control-takes-label')
        this.htmlItem.baseElement.classList.add('has-edge')

        this.link(this.eventDispatcher.onClick,() => {
            let shift = Vector2.fromPolar(17*3,this.orientation)
            shift = shift.add(new Vector2(0,-17))
            if(this.is_input.getValue()){
                shift = shift.add(new Vector2(-17*8,0))
            }
            this.node.editor.slashCommandMenu.openMenu({
                attached_port:this.id, 
                translation:(this.node.editor.transform.othersToLocal(this.transform).add(shift)).toList()})
        })

        this.link(this.display_name.onSet,(label: string) => {
            this.labelDiv.innerText = label
        })
        this.link(this.is_input.onSet,(is_input: number) => {
            if(is_input) {
                this.orientation = Math.PI
            }else{
                this.orientation = 0
            }
            this.isInputChanged(this.is_input.getValue())
        })
        this.link(this.max_edges.onSet,this.updateAcceptsEdgeClass)


        if(this.is_input.getValue()) {
            this.link(this.getAttribute('update_control_from_edge').onSet,(value: boolean) => {
                if(value) {
                    this.htmlItem.baseElement.classList.remove('hide-control-if-has-edge')
                }
                else {
                    this.htmlItem.baseElement.classList.add('hide-control-if-has-edge')
                }
            })
            this.link(this.getAttribute('control_takes_label').onSet,(takes_label: number) => {
                if(takes_label) {
                    this.htmlItem.baseElement.classList.add('control-takes-label')
                } else {
                    this.htmlItem.baseElement.classList.remove('control-takes-label')
                }
            })
            if(this.getAttribute('control_takes_label').getValue()) {
                this.htmlItem.baseElement.classList.add('control-takes-label')
            } else {
                this.htmlItem.baseElement.classList.remove('control-takes-label')
            }
        }else{
            this.htmlItem.baseElement.classList.remove('control-takes-label')
        }
        if(this.edges.length === 0){
            this.htmlItem.baseElement.classList.remove('has-edge')
        }
        this.eventDispatcher.isDraggable = (e:MouseEvent)=>!(this.node.isPreview ||
                    !this.acceptsEdge() ||
                    e.buttons !== 1)
    }


    protected onParentChangedFrom(oldValue: CompSObject): void {
        super.onParentChangedFrom(oldValue)
        this.isInputChanged(this.is_input.getValue())
        if(oldValue.hasComponent(Transform))
            as(oldValue,Node).moved.remove(this.moved.invoke)
    }

    protected onParentChangedTo(newValue: CompSObject): void {
        super.onParentChangedTo(newValue)
        this.isInputChanged(this.is_input.getValue())
        this.node = as(newValue, Node);
        if(this.node.hasComponent(Transform))
            this.node.moved.add(this.moved.invoke)
        this.moved.invoke()
    }



    public acceptsEdge(delta:number=0): boolean {
        if(this.node!=null && this.node.isPreview) return false
        if (this.type_incompatible) return false
        if(this.max_edges.getValue() > this.edges.length+delta) return true
        return false
    }

    public getTypeUnconnectablePortsId(): Promise<string[]> {
        return new Promise((resolve) => {
            this.makeRequest("get_type_unconnectable_ports",{}, resolve)
        })
    }

    private isInputChanged(is_input: number): void {
        if(is_input) {
            this.htmlItem.setParent(this.getComponentInAncestors(HtmlItem)!, 'input_port')
            this.knob.classList.remove('out-port')
            this.knob.classList.add('in-port')
        } else {
            this.htmlItem.setParent(this.getComponentInAncestors(HtmlItem)!, 'output_port')
            this.knob.classList.remove('in-port')
            this.knob.classList.add('out-port')
        }
        this.moved.invoke()
    }

    private generateEdge(e:MouseEvent): void {
        this.objectsync.clearPretendedChanges()
        this.objectsync.record((() => {
            let newEdge = as(this.objectsync.createObject('Edge', this.parent.parent.id),Edge)
            if(this.is_input.getValue()){
                newEdge.addTag('CreatingDragTail')
                newEdge.head.set(this)
            }
            else{
                newEdge.addTag('CreatingDragHead')
                newEdge.tail.set(this)
            }
        }),true)
    }

    private updateAcceptsEdgeClass(): void {
        if(this.acceptsEdge()){
            this.knob.classList.add('accepts-edge')
            this.hitbox.classList.add('accepts-edge')
        }
        else{
            this.knob.classList.remove('accepts-edge')
            this.hitbox.classList.remove('accepts-edge')
        }
    }
}