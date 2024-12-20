import {ObjectSyncClient, SObject, StringTopic, FloatTopic, ListTopic, ObjListTopic, Action, IntTopic, SetTopic} from 'objectsync-client'
import { fetchWithCache, soundManager } from '../app'
import { HtmlItem } from '../component/htmlItem'
import { Space, Transform } from '../component/transform'
import { CompSObject } from './compSObject'
import { print } from '../devUtils'
import { Port } from './port'
import { bloomDiv as bloomDiv, glowText } from '../ui_utils/effects'
import { Vector2, as } from '../utils'
import { EventDispatcher, GlobalEventDispatcher } from '../component/eventDispatcher'
import { MouseOverDetector } from '../component/mouseOverDetector'
import { NodeLibrary } from './nodeLibrary'
import { Editor } from './editor'
import { Selectable } from '../component/selectable'
import { Workspace } from './workspace'
import { ErrorPopup } from '../ui_utils/errorPopup'
import { ExposedAttributeInfo } from '../inspector/inspector'
import { IControlHost } from './controls/controlHost'
 
export class Node extends CompSObject implements IControlHost {
    errorPopup: ErrorPopup;
    public static getCssClassesFromCategory(category: string): string[]{
        let classes = []
        let str = 'cate'
        for(let subCat of category.split('/')){
            if(subCat == '') continue
            str += '-'+subCat.replace(/[^a-zA-Z0-9]/g,'-')
            str = str.toLowerCase()
            classes.push(str)
        }
        return classes
    }

    shape: StringTopic = this.getAttribute('shape', StringTopic) // normal, simple, round
    label: StringTopic = this.getAttribute('label', StringTopic)
    label_offset: FloatTopic = this.getAttribute('label_offset', FloatTopic)
    translation: StringTopic = this.getAttribute('translation', StringTopic)
    category: StringTopic = this.getAttribute('category', StringTopic)
    in_ports: ObjListTopic<Port> = this.getAttribute('in_ports', ObjListTopic<Port>)
    out_ports: ObjListTopic<Port> = this.getAttribute('out_ports', ObjListTopic<Port>)
    exposed_attributes: ListTopic<ExposedAttributeInfo> = this.getAttribute('exposed_attributes', ListTopic<ExposedAttributeInfo>)
    type_topic: StringTopic = this.getAttribute('type', StringTopic)
    output: ListTopic<[string,string]> = this.getAttribute('output', ListTopic<[string,string]>)
    css_classes: SetTopic = this.getAttribute('css_classes', SetTopic)
    icon_path: StringTopic = this.getAttribute('icon_path', StringTopic)
    
    private _isPreview: boolean
    get isPreview(): boolean {
        return this._isPreview
    }


    editor: Editor;
    ancestorNode: Node = this;

    dragEndCorrection: Vector2 = new Vector2(0,0)
    private draggingTargetPos: Vector2 = new Vector2(0,0)
    
    public moved: Action<[]> = new Action();

    protected readonly templates: {[key: string]: string} = {
    normal: 
        `<div class="node normal-node" slot="default">
            
            
            <div class="node-selection"></div>
            <div class="node-label full-width">
                <div class="node-label-underlay"></div>
                <div ref="labelDiv"></div>
            </div>

            <div class="node-border-container">
                <div class="node-border" id="node-border">
                </div>
            </div>
            <div class=" flex-vert space-between main-section">
                <div slot="input_port" class=" flex-vert space-evenly slot-input-port"></div>
                <div slot="output_port" class=" flex-vert space-evenly slot-output-port"></div>
                <div slot="control" class="slot-control flex-vert space-between"></div>
                <div slot="param_input_port" class=" flex-vert space-evenly slot-input-port  slot-param-input-port"></div>
            </div>
        </div>`,
    simple:
        `<div class="node simple-node" slot="default">

            <div class="node-selection"></div>
            
            <div class="flex-horiz stretch-align space-between">
                <div class="flex-vert justify-start">
                    <div slot="input_port" class=" flex-vert justify-start slot-input-port"></div>
                    <div slot="param_input_port" class=" flex-vert justify-start slot-input-port slot-param-input-port"></div>
                </div>

                <div class="full-width flex-vert space-evenly">
                    <div class="node-label full-width flex-horiz">
                        <div class="node-label-underlay"></div>
                        <div ref="labelDiv"></div>
                    </div>
                    <div class="node-border-container">
                        <div class="node-border"id="node-border">
                        </div>
                    </div>
                    <div slot="control"  class="slot-control main-section"></div>
                </div>

                <div slot="output_port" class=" flex-vert justify-start slot-output-port"></div>
            </div>
        </div>`,
    round:
        `<div class="node round-node " slot="default">
            <div class="node-border-container">
                <div class="node-border"id="node-border">
                </div>
            </div>
            <div class="node-selection"></div>
            <div class="flex-horiz node-content">
                <div slot="input_port" class=" flex-vert space-evenly slot-input-port"></div>
                <div slot="param_input_port" class=" flex-vert space-evenly slot-input-port slot-param-input-port"></div>
                <div class="full-width flex-vert space-evenly node-label"> 
                    <div class="node-label-underlay"></div>
                    <div ref="labelDiv" class="center-align"></div>
                </div>
                <div slot="control" style="display:none"></div>
                
                <div slot="output_port" class=" flex-vert space-evenly slot-output-port"></div>
            </div>
        </div>`,
    }

    private readonly labelDiv: HTMLDivElement

    constructor(objectsync: ObjectSyncClient, id: string) {
        super(objectsync, id)
        this.errorPopup = new ErrorPopup(this)
        this.htmlItem// Ensure htmlItem is created
    }

    protected onStart(): void {
        super.onStart()

        this._isPreview = this.parent instanceof NodeLibrary
        this.editor = this.isPreview? null : this.parent as Editor
        this.selectable.selectionManager = Workspace.instance.selection
        if (!this.isPreview)
            this.transform.positionAbsolute = true

        // Bind attributes to UI
        

        this.link(this.shape.onSet,this.reshape)

        this.link(this.label.onSet, (label: string) => {
            this.labelDiv.innerText = label
        })

        this.link(this.label_offset.onSet, (offset: number) => {
            let label_el = this.labelDiv
            label_el.style.marginTop = offset + 'em'
        })


        this.link(this.category.onSet2, (oldCategory: string, newCategory: string) => {
            if(this.parent instanceof NodeLibrary){
                if(this.parent.hasItem(this.htmlItem))
                    this.parent.removeItem(this.htmlItem, oldCategory)
                this.parent.addItem(this.htmlItem, newCategory)
            }
            for(let className of Node.getCssClassesFromCategory(oldCategory)){
                this.htmlItem.baseElement.classList.remove(className)
            }
            for(let className of Node.getCssClassesFromCategory(newCategory)){
                this.htmlItem.baseElement.classList.add(className)
            }
        })

        if (!this.isPreview){

            this.link(this.eventDispatcher.onDoubleClick, () => {
                if(this.shape.getValue() == 'normal'){
                    this.shape.set('simple')
                }else{
                    this.shape.set('normal')
                }
            })
            this.link(this.editor.runningChanged.slice(this), (running: boolean) => {
                if(running == true)
                    this.htmlItem.baseElement.classList.add('running')
                else{
                    this.htmlItem.baseElement.classList.remove('running')
                }
            }) 

            if (this.editor.isRunning(this)) this.htmlItem.baseElement.classList.add('running')
        }


        this.link(this.output.onInsert, ([type, value]: [string, string]) => {
                if(type == 'error'){
                this.objectsync.doAfterTransitionFinish(() => { 
                    // Sometimes onInsert is invoked by reverted preview change.
                    if(this.output.getValue().length == 0) return
                    this.errorPopup.set('Error',value)
                    this.errorPopup.show()
                    })
                }
        })

        // Configure components
        
        if (!this.isPreview){ 
            this.htmlItem.setParent(this.editor.htmlItem)
        }

        // Before setting up the transform, we need to add classes to the element so the shape is correct
        
        this.link(this.css_classes.onAppend, (className: string) => {
            this.htmlItem.baseElement.classList.add(className)
        })
        
        this.link(this.css_classes.onRemove, (className: string) => {
            this.htmlItem.baseElement.classList.remove(className)
        })
        
        for(let className of this.css_classes.getValue()){
            this.htmlItem.baseElement.classList.add(className)
        }
        
        // Setup the transform
        if (!this.isPreview){
            this.transform.updateUI()
            this.transform.pivot = new Vector2(0,0)
        
            this.translation.onSet.add((translation: string) => {
                if(!this.eventDispatcher.isDragging){ // prevent the node from jumping when dragging
                    let v = Vector2.fromString(translation);
                    if(!Number.isNaN(v.x) && !Number.isNaN(v.y))
                        this.transform.translation=Vector2.fromString(translation)
                }
            })

            this.link(this.eventDispatcher.onMouseDown, (e: MouseEvent) => {
                // pass the event to the editor to box select
                if(e.ctrlKey){
                    this.eventDispatcher.forwardEvent()
                    return
                }
            })

            this.link(this.eventDispatcher.onMouseDown,(e: MouseEvent) => {
                // pass the event to the editor
                if(e.buttons != 1) this.eventDispatcher.forwardEvent()
            })
            
            // the node is only draggable when the left mouse button is pressed
            this.eventDispatcher.isDraggable = (e)=> {
                if (e.buttons != 1) return false
                if(e.ctrlKey) return false
                return true
            }

            this.link(this.eventDispatcher.onDragStart,(e: MouseEvent,pos: Vector2) => {
                this.draggingTargetPos = this.transform.translation
                this.htmlItem.baseElement.classList.add('dragging')
            })

            this.link(this.eventDispatcher.onDrag,(e: MouseEvent,newPos: Vector2,oldPos: Vector2) => {
                if(!this.selectable.selectionManager.enabled && !this.selectable.selected) return;
                if(!this.selectable.selected) this.selectable.click()

                let delta = this.transform.worldToLocalDisplacement(newPos.sub(oldPos))
                let snappedDelta = delta
                if(!GlobalEventDispatcher.instance.isKeyDown('Alt')){
                    this.draggingTargetPos = this.draggingTargetPos.add(delta)
                    const snap = 17
                    let snapped = new Vector2(
                        Math.round(this.draggingTargetPos.x/snap)*snap,
                        Math.round(this.draggingTargetPos.y/snap)*snap
                    )
                    const delta2 = snapped.sub(this.draggingTargetPos)
                    this.dragEndCorrection = delta2.mulScalar(0.1)
                    snapped = snapped.sub(delta2.mulScalar(0.1))
                    snappedDelta = snapped.sub(this.transform.translation)
                }

                for(let selectable of this.selectable.selectedObjects){
                    if(selectable.object instanceof Node){
                        let node = selectable.object
                        node.transform.translate(snappedDelta,Space.Local)
                        node.htmlItem.moveToFront()
                    }
                }
            })
            this.link(this.eventDispatcher.onDragEnd,(e: MouseEvent,pos: Vector2) => {
                this.objectsync.record(() => {
                    for(let selectable of this.selectable.selectedObjects){
                        if(selectable.object instanceof Node){
                            let node = selectable.object
                            node.transform.translate(this.dragEndCorrection,Space.Local)
                            node.translation.set(node.transform.translation.toString())
                        }
                    }
                })
                this.htmlItem.baseElement.classList.remove('dragging')
            })
        }

        if(this.isPreview){
            this.link(this.eventDispatcher.onDragStart, () => {
                //create a new node
                this.emit('spawn',{client_id:this.objectsync.clientId}) 
            })
            this.selectable.enabled = false
        }
        
        this.link(this.selectable.onSelected, () => {
            this.htmlItem.baseElement.classList.add('selected')
        })

        this.link(this.selectable.onDeselected, () => {
            this.htmlItem.baseElement.classList.remove('selected')
        })  


        this.link(this.eventDispatcher.onMouseOver, () => {
            this.htmlItem.baseElement.classList.add('hover')
        })

        this.link(this.eventDispatcher.onMouseLeave, () => {
            this.htmlItem.baseElement.classList.remove('hover')
        })

        this.link(this.onAddChild,this.moved.invoke)
        this.link(this.onRemoveChild,this.moved.invoke)
        if(!this.isPreview){
            this.link(this.transform.onChange,this.moved.invoke)
            this.transform.updateUI() // This line is necessary to make edges spawning in this frame to be connected to the node
        }
    }

    protected postStart(): void {
        // called after all the children are set up
        super.postStart()
        
        if(this.hasTag(`drag_created_by${this.objectsync.clientId}`))
        {
            this.removeTag(`drag_created_by${this.objectsync.clientId}`)
            this.selectable.click()
            let pivot = this.transform.pivot
            this.transform.globalPosition = this.eventDispatcher.mousePos.add(pivot.mul(this.transform.size)).add(this.transform.size.mulScalar(-0.5))
            this.eventDispatcher.fakeOnMouseDown() //fake a mouse down to start dragging
        }
        
        if(this.hasTag(`pasted_by_${this.objectsync.clientId}`))
        {
            this.removeTag(`pasted_by_${this.objectsync.clientId}`)
            this.selectable.select()
            // focus the first input or .cm-editor element in the node
            let input = this.htmlItem.baseElement.querySelector('.code-control') as HTMLElement
            || this.htmlItem.baseElement.querySelector('textarea')
            || this.htmlItem.baseElement.querySelector('input');

            if(input) input.focus()
        }
        
        if(this.hasTag(`created_by_${this.objectsync.clientId}`))
        {
            this.removeTag(`created_by_${this.objectsync.clientId}`)
            this.selectable.select()
            // focus the first input or .cm-editor element in the node
            let input = this.htmlItem.baseElement.querySelector('.code-control') as HTMLElement
            || this.htmlItem.baseElement.querySelector('textarea')
            || this.htmlItem.baseElement.querySelector('input') 
            
            
            if(input) input.focus();
            (window as any).i = input
        }
        this.portVisibilityChanged()
    }

    setIcon(path: string){
        fetchWithCache('svg/list.txt')
        .then(list => {
            if(list.replaceAll('\r','').split('\n').indexOf(path) != -1){
                this.setIconFromSvg(`svg/${path}.svg`)
            }
        })
    }

    setIconFromSvg(path: string){
        const base = (this.htmlItem.getElByClass('node-label') as HTMLDivElement)
        // load svg from url
        // the reason not using img tag is because its tint color cannot be changed by css
        fetchWithCache(path)
        .then(svg => {
            // skip if node-icon already exists. Not sure why this is necessary
            if(base.querySelector('.node-icon') != null) return
            let t = document.createElement('template')
            t.innerHTML = svg
            let svgEl = null;
            for(let child of t.content.childNodes){
                if(child instanceof SVGElement){
                    svgEl = child
                    break
                }
            }
            if(svgEl == null) return
            base.prepend(svgEl)
            for(let dec of svgEl.querySelectorAll('path,rect,g')){
                // if fill is black, change it to currentColor
                if((dec as SVGElement).getAttribute('fill') == '#000000'){
                        
                    (dec as HTMLElement).style.fill = ''
                    dec.setAttribute('fill','')
                }
            }
            svgEl.classList.add('node-icon')
            this.link2(svgEl,'click',() => {
                this.emit('icon_clicked')
            })
            if(path == 'svg/task.svg'){
                // change cursor to pointer
                svgEl.style.cursor = 'pointer'
            }
            this.moved.invoke()
        })   
    }

    onParentChangedTo(newParent: SObject): void {
        super.onParentChangedTo(newParent)
        if(newParent instanceof NodeLibrary){
            newParent.addItem(this.htmlItem, this.category.getValue())
            if(!this.isPreview)
                this.transform.enabled = false
        }
        else{
            this.htmlItem.setParent(this.getComponentInAncestors(HtmlItem))
            this.errorPopup.htmlItem.setParent(this.htmlItem.parent)
        }
        if(newParent instanceof Node){
            as(this.htmlItem.baseElement,HTMLDivElement).style.borderColor = 'transparent'
            if(!this.isPreview)
                this.transform.enabled = false
        }
    }

    reshape(shape: string) {
        this.applyTemplate(this.templates[shape])
        this.eventDispatcher.setEventElement(as(this.htmlItem.baseElement, HTMLElement))
        this.mouseOverDetector.eventElement = this.htmlItem.baseElement
        
        this.labelDiv.innerText = this.label.getValue()
        
        this.link2(this.htmlItem.baseElement,'mousedown', () => {
            soundManager.playClick()
        })
        
        this.labelDiv.style.marginTop = this.label_offset.getValue() + 'em'

        if(this._isPreview){
            this.htmlItem.baseElement.classList.add('node-preview')
            const node_types_topic = Workspace.instance.nodeTypesTopic
            let nodeTypeDescription = node_types_topic.getValue().get(this.type_topic.getValue()).description
            this.htmlItem.baseElement.setAttribute('title', nodeTypeDescription)

        }

        if(shape == 'round'){
            this.htmlItem.baseElement.classList.add('round-node');
            (this.htmlItem.baseElement as HTMLElement).style.minWidth = 'unset'
        }else{
            (this.htmlItem.baseElement as HTMLElement).style.minWidth = this.minWidth + 'px'
        }

        for(let className of Node.getCssClassesFromCategory(this.category.getValue())){
            this.htmlItem.baseElement.classList.add(className)
        }

        for(let className of Node.getCssClassesFromCategory(this.category.getValue())){
            this.htmlItem.baseElement.classList.add(className)
        }

        if(this.icon_path.getValue() != ''){
            this.setIcon(this.icon_path.getValue())
        }

        this.portVisibilityChanged()
    }

    private minWidth: number = 0;

    public setMinWidth(width: number): void {
        if(width < this.minWidth) return
        this.minWidth = width;
        if(this.shape.getValue() != 'round')
            (this.htmlItem.baseElement as HTMLElement).style.minWidth = width + 'px'
    }

    public onDestroy(): void {
        super.onDestroy()
        if(this.parent instanceof NodeLibrary){
            this.parent.removeItem(this.htmlItem, this.category.getValue())
        }
        this.errorPopup.destroy()
    }

    public portVisibilityChanged(): void {
        let hasVisibleInput = false
        let hasVisibleParam = false
        let hasVisibleOutput = false

        for(let port of this.in_ports.getValue()){
            if(!port.hidden){
                if(port.is_param.getValue()){
                    hasVisibleParam = true
                }
                else{
                    hasVisibleInput = true
                }
            }
        }
        for(let port of this.out_ports.getValue()){
            if(!port.hidden){
                hasVisibleOutput = true
            }
        }

        if(hasVisibleInput){
            this.htmlItem.baseElement.classList.add('has-visible-input')
        }
        else{
            this.htmlItem.baseElement.classList.remove('has-visible-input')
        }

        if(hasVisibleOutput){
            this.htmlItem.baseElement.classList.add('has-visible-output')
        }
        else{
            this.htmlItem.baseElement.classList.remove('has-visible-output')
        }

        if(hasVisibleParam){
            this.htmlItem.baseElement.classList.add('has-visible-param')
        }
        else{
            this.htmlItem.baseElement.classList.remove('has-visible-param')
        }
    }
}