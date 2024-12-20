import { ObjectSyncClient, ObjectTopic, SObject, StringTopic } from 'objectsync-client'
import { soundManager } from '../app'
import { HtmlItem } from '../component/htmlItem'
import { MouseOverDetector } from '../component/mouseOverDetector'
import { Vector2, as } from '../utils'
import { CompSObject } from './compSObject'
import { Editor } from './editor'
import { Port } from './port'
import { Workspace } from './workspace'

enum EdgeState {
    Idle,
    DraggingTail,
    DraggingHead,
}

interface PathResult {
    tangent: Vector2;
    normal: Vector2;
    length: number;
    points: Vector2[];
}

export class Edge extends CompSObject {

    /* Template */
    get template(): string { return`
    <div ref="base" id="base" style="position:absolute;width:1px;height:1px">
        <div ref="label" class="edge-label"></div>
        <svg ref="svg" class="edge">
            <g>
                <path ref="path" class="edge-path"d=""  fill="none"></path>
                <path ref="path_hit_box" class="edge-path-hit-box"d=""  fill="none"></path>
                <circle ref="dot" class="edge-dot"cx="0" cy="0" r="2" fill="none"></circle>
            </g>
        </svg>
    </div>
    `}

    get style(): string { return`
    .svg {
        position: absolute;
        width: auto;
        height: auto;
    }
    .base {
        width: 1px;
        height: 1px;
    }
    `}

    /* Element References */
    base: HTMLDivElement
    path: SVGPathElement
    path_hit_box: SVGPathElement
    svg: SVGSVGElement
    label: HTMLDivElement
    dot: SVGCircleElement

    /* Attributes */
    tail = this.getAttribute('tail', ObjectTopic<Port>)
    head = this.getAttribute('head', ObjectTopic<Port>)
    labelTopic = this.getAttribute('label', StringTopic)

    /* Other Fields */
    editor: Editor
    dotAnimation: DotAnimation
    _state: EdgeState = EdgeState.Idle
    get state(): EdgeState { return this._state }
    set state(value: EdgeState) {
        console.log(`Edge id: ${this.id} from state: ${EdgeState[this._state]}`)
        this._state = value
        console.log(`Edge id: ${this.id} set to state: ${EdgeState[value]}`)
        if(value == EdgeState.DraggingTail || value == EdgeState.DraggingHead) {
            let connected_port = value == EdgeState.DraggingTail ? this.head : this.tail
            connected_port.getValue()?.getTypeUnconnectablePortsId().then((portsId: string[]) => {
                for(let id of portsId){
                    as(this.objectsync.getObject(id), Port).type_incompatible = true
                }
            })
        } else {
            // Since edge is idle now, the type_incompatible of all ports should be false
            this.cancelTypeConstraints()
        }
    }

    constructor(objectsync: ObjectSyncClient, id: string) {
        super(objectsync, id)
        this.editor = this.parent as Editor
        this.dotAnimation = new DotAnimation(this.dot)
    }

    protected onStart(): void {
        super.onStart()

        this.eventDispatcher.setEventElement(this.path_hit_box)
        this.selectable.selectionManager = Workspace.instance.selection

        
        this.transform.pivot = Vector2.zero
        this.transform.translation = Vector2.zero
        this.transform.positionAbsolute = true

        // link attributes to UI

        this.link(this.eventDispatcher.onClick, () => {
            soundManager.playClick() // why not working?
        })

        if(this.hasTag('CreatingDragTail')) this.state = EdgeState.DraggingTail
        if(this.hasTag('CreatingDragHead')) this.state = EdgeState.DraggingHead
        if(this.hasTag('CreatingDragTail')||this.hasTag('CreatingDragHead')){
            this.link(this.eventDispatcher.onMoveGlobal,this.onDrag)
            this.link(this.eventDispatcher.onMouseUpGlobal,this.onDragEndWhileCreating)
        }else{
            this.eventDispatcher.onMouseDown.add((e: MouseEvent) => {
                // pass the event to the editor
                if(e.buttons != 1) this.eventDispatcher.forwardEvent()
            })
            this.link(this.eventDispatcher.onDragStart,this.onDragStart)
            this.link(this.eventDispatcher.onDrag,this.onDrag)
            this.link(this.eventDispatcher.onDragEnd,this.onDragEnd)
            this.link(this.eventDispatcher.onMouseOver,() => {
                this.svg.classList.add('hover')
            })
            this.link(this.eventDispatcher.onMouseLeave,() => {
                this.svg.classList.remove('hover')
            })
        }

        
        this.onPortChanged(null,this.tail.getValue())
        this.onPortChanged(null,this.head.getValue())
        this.link(this.tail.onSet2,this.onPortChanged)
        this.link(this.head.onSet2,this.onPortChanged)

        this.link(this.selectable.onSelected, () => {
            this.svg.classList.add('selected')
        })

        this.link(this.selectable.onDeselected, () => {
            this.svg.classList.remove('selected')
        })
        this.link(this.labelTopic.onSet, () => {
            this.label.innerText = this.labelTopic.getValue()
        })

        this.updateSVG()


        this.link(this.eventDispatcher.onMouseDown, (e: MouseEvent) => {
            // pass the event to the editor to box select
            if(e.ctrlKey){
                this.eventDispatcher.forwardEvent()
                return
            }
        })


    }

    private onPortChanged (oldPort:Port,newPort:Port) : void{
        if(oldPort){
            this.unlink(oldPort.moved)
            oldPort.removeEdge(this)
        }
        if(newPort){
            this.updateSVG()
            this.link(newPort.moved,this.updateSVG)
            newPort.addEdge(this)
        }
    }

    onDestroy(): void {
        if(this.tail.getValue()) {
            this.tail.getValue().moved.remove(this.updateSVG)
        }
        if(this.head.getValue()) {
            this.head.getValue().moved.remove(this.updateSVG)
        }
        this.head.getValue()?.removeEdge(this)
        this.tail.getValue()?.removeEdge(this)
        this.dotAnimation.stopImmediately()
        super.onDestroy()
    }

    protected onParentChangedTo(newValue: SObject): void {
        super.onParentChangedTo(newValue)
        this.htmlItem.setParent(this.getComponentInAncestors(HtmlItem) || this.editor.htmlItem) //>????????????
        this.updateSVG()
        this.editor = as(newValue, Editor)
        this.link(this.editor.runningChanged.slice(this), (data_ready: boolean) => {
            if(data_ready){
                this.svg.classList.add('data-ready')
                this.dotAnimation.start()
            }
            else{
                
                this.svg.classList.remove('data-ready')
                this.dotAnimation.stop()
            }
        })
        
        // initialize data ready
        if(this.editor.isRunning(this)){
            this.svg.classList.add('data-ready')
            this.dotAnimation.start()
        }

    }

    private cancelTypeConstraints() {
        for(let port of this.editor.TopDownSearch(Port)){
            port.type_incompatible = false
        }
    }

    private onDragStart(event: MouseEvent, mousePos: Vector2) {
        if(event.ctrlKey || event.shiftKey || event.buttons != 1) { return }
        let maxR = 200
        let distToTail = this.tail.getValue().transform.worldCenter.distanceTo(mousePos)
        let distToHead = this.head.getValue().transform.worldCenter.distanceTo(mousePos)
        //if(distToTail > maxR && distToHead > maxR)return;
        if(distToTail < distToHead) {
            this.state = EdgeState.DraggingTail
        }
        else {
            this.state = EdgeState.DraggingHead
        }
    }

    private onDrag(e: MouseEvent, mousePos: Vector2) {
        e.preventDefault()
        let candidatePorts: Port[] = []
        for(let object of MouseOverDetector.objectsUnderMouse){
            if(object instanceof Port){
                let port = object
                if(this.state == EdgeState.DraggingTail){
                    const delta = port == this.tail.getValue() ? -1:0
                    if(!port.is_input.getValue() && port.acceptsEdge(delta)){
                        candidatePorts.push(port)
                    }
                }
                else if(this.state == EdgeState.DraggingHead){
                    const delta = port == this.head.getValue() ? -1:0
                    if(port.is_input.getValue() && port.acceptsEdge(delta)){
                        candidatePorts.push(port)
                    }
                }
            }
        }

        if(candidatePorts.length == 0){
            if(this.state == EdgeState.DraggingTail){
                this.objectsync.record(() => {
                    this.tail.set(null)
                },true)
            }
            else if(this.state == EdgeState.DraggingHead){
                this.objectsync.record(() => {
                    this.head.set(null)
                },true)
            }
            this.updateSVG()
            return
        }

        let nearestPort: Port | null = null
        let nearestPortDist = Infinity
        for(let port of candidatePorts){
            let dist = port.transform.worldCenter.distanceTo(mousePos)
            if(dist < nearestPortDist){
                nearestPort = port
                nearestPortDist = dist
            }
        }

        if(nearestPort == this.tail.getValue() || nearestPort == this.head.getValue()){
            this.updateSVG();
            return;
        }

        if(this.state == EdgeState.DraggingTail){
            this.objectsync.record(() => {
                this.tail.set(nearestPort)
            },true)
        }else{
            this.objectsync.record(() => {
                this.head.set(nearestPort)
            },true)
        }

        if(this.state == EdgeState.DraggingTail || this.state == EdgeState.DraggingHead) {
            this.updateSVG()
        }
    }

    private onDragEnd(event: MouseEvent, mousePos: Vector2) {
        if(this.state == EdgeState.DraggingTail &&
            (this.tail.getValue() == null || !MouseOverDetector.objectsUnderMouse.includes(this.tail.getValue())))
            {
                this.objectsync.clearPretendedChanges();
                this.objectsync.destroyObject(this.id);
            }
        else if(this.state == EdgeState.DraggingHead &&
            (this.head.getValue() == null || !MouseOverDetector.objectsUnderMouse.includes(this.head.getValue())))
            {
                this.objectsync.clearPretendedChanges();
                this.objectsync.destroyObject(this.id);
            }
        else {
            // make the change of port permanent
            if (this.state == EdgeState.DraggingTail) {
                let newTail = this.tail.getValue()
                this.objectsync.clearPretendedChanges();
                this.tail.set(newTail)
                this.updateSVG()
            }
            else if (this.state == EdgeState.DraggingHead) {
                let newHead = this.head.getValue()
                this.objectsync.clearPretendedChanges();
                this.head.set(newHead)
                this.updateSVG()
            }
        }
        this.state = EdgeState.Idle
    }

    private onDragEndWhileCreating(){

        if(this.state == EdgeState.DraggingTail &&
            (this.tail.getValue() == null || !MouseOverDetector.objectsUnderMouse.includes(this.tail.getValue())))
            {
                this.editor.slashCommandMenu.openMenu({
                    attached_port:this.head.getValue().id,
                    translation:this.editor.transform.worldToLocal(this.eventDispatcher.mousePos).add(new Vector2(-17*6,0)).toList()
                })
                this.objectsync.clearPretendedChanges();
            }
        else if(this.state == EdgeState.DraggingHead &&
            (this.head.getValue() == null || !MouseOverDetector.objectsUnderMouse.includes(this.head.getValue())))
            {
                this.editor.slashCommandMenu.openMenu({
                    attached_port:this.tail.getValue().id,
                    translation:this.editor.transform.worldToLocal(this.eventDispatcher.mousePos).toList()
                })
                this.objectsync.clearPretendedChanges();
            }
        else {
            // make the change of port permanent
            let tail = this.tail.getValue()
            let head = this.head.getValue()
            this.editor.createEdge(tail.id,head.id)
            this.objectsync.clearPretendedChanges();
        }
        this.state = EdgeState.Idle
    }


    // Graphical stuff
    private updateSVG() {
        this._updateSVG()
        setTimeout(() => {
            try{
                this._updateSVG()
            }catch(e){}
        }, 0);
    }

    private _updateSVG() {
        let path = this.getSVGPath()
        if(path==null)return//no change
        this.path.setAttribute('d', path)
        this.path_hit_box.setAttribute('d', path)
        let worldCenter = new Vector2(
            (this.path.getBoundingClientRect().left + this.path.getBoundingClientRect().right)/2,
            (this.path.getBoundingClientRect().top + this.path.getBoundingClientRect().bottom)/2
        )
        let localCenter = this.transform.worldToLocal(worldCenter)
        this.label.style.left = localCenter.x + 'px'
        this.label.style.top = localCenter.y + 'px'
        this.label.style.width = this.pathResult.length + 'px'
        let angle = this.pathResult.tangent.angle()
        if (angle > Math.PI/2) angle -= Math.PI
        if (angle < -Math.PI/2) angle += Math.PI
        this.label.style.transform = `translate(-50%,-50%) rotate(${angle}rad) translate(0,50%)`
        this.dotAnimation.setPathResult(this.pathResult)
    }

    pathParam = {
        tail:new Vector2(NaN,NaN),
        head:new Vector2(NaN,NaN),
        tail_orientation:-1,
        head_orientation:-1
    }

    pathResult: PathResult = {
        tangent:new Vector2(NaN,NaN),
        normal:new Vector2(NaN,NaN),
        length:NaN,
        points:[new Vector2(NaN,NaN),new Vector2(NaN,NaN),new Vector2(NaN,NaN),new Vector2(NaN,NaN)]
    }

    private getSVGPath(): string {
        let tail: Vector2
        let head: Vector2
        let tail_orientation: number
        let head_orientation: number

        if(
            this.state == EdgeState.DraggingTail &&
            this.head.getValue() != null &&
            (this.tail.getValue() == null || !MouseOverDetector.objectsUnderMouse.includes(this.tail.getValue()))){
            tail = this.transform.worldToLocal(this.eventDispatcher.mousePos)
            head = this.transform.worldToLocal(this.head.getValue().transform.worldCenter)
            //tail_orientation = Math.atan2(head.y - tail.y, head.x - tail.x)
            tail_orientation = 0
            head_orientation = this.head.getValue().orientation
        }
        else if(
            this.state == EdgeState.DraggingHead &&
            this.tail.getValue() != null &&
            (this.head.getValue() == null || !MouseOverDetector.objectsUnderMouse.includes(this.head.getValue()))) {
            tail = this.transform.worldToLocal(this.tail.getValue().transform.worldCenter)
            head = this.transform.worldToLocal(this.eventDispatcher.mousePos)
            tail_orientation = this.tail.getValue().orientation
            //head_orientation = Math.atan2(tail.y - head.y, tail.x - head.x)
            head_orientation = Math.PI
        }else {
            if(!this.tail.getValue() || !this.head.getValue()) {throw Error;}
            tail = this.transform.worldToLocal(this.tail.getValue().transform.worldCenter)
            head = this.transform.worldToLocal(this.head.getValue().transform.worldCenter)
            tail_orientation = this.tail.getValue().orientation
            head_orientation = this.head.getValue().orientation
        }

        if(tail.equals(this.pathParam.tail) &&
            head.equals(this.pathParam.head) &&
            tail_orientation == this.pathParam.tail_orientation &&
            head_orientation == this.pathParam.head_orientation
        )return null // no change

        this.pathParam = {tail,head,tail_orientation,head_orientation}

        let dx = head.x - tail.x
        let dy = head.y - tail.y
        let d = Math.sqrt(dx*dx + dy*dy)
        let r1 = Math.min(50, d/3) + 4*Math.sqrt(Math.max(0,- (dx*Math.cos(tail_orientation) + dy*Math.sin(tail_orientation))))
        let r2 = Math.min(50, d/3) + 4*Math.sqrt(Math.max(0,(dx*Math.cos(head_orientation) + dy*Math.sin(head_orientation))))
        if(isNaN(r1+r2) || isNaN(tail_orientation) || isNaN(head_orientation)) throw new Error('NaN')
        let mp1 = new Vector2(tail.x + Math.cos(tail_orientation)*r1, tail.y + Math.sin(tail_orientation)*r1)
        let mp2 = new Vector2(head.x + Math.cos(head_orientation)*r2, head.y + Math.sin(head_orientation)*r2)
        let path = `M ${tail.x} ${tail.y} C ${mp1.x} ${mp1.y} ${mp2.x} ${mp2.y} ${head.x} ${head.y}`

        this.pathResult = {
            tangent:mp2.add(head).sub(mp1.add(tail)).normalized(),
            normal:mp2.add(head).sub(mp1.add(tail)).normalized().rotate(Math.PI/2),
            length:d,
            points:[tail,mp1,mp2,head]
        }

        // let dx = head.x - tail.x
        // let dy = head.y - tail.y
        // let d = Math.sqrt(dx*dx + dy*dy)
        // let r = Math.min(50, d/2)
        // if(isNaN(r) || isNaN(tail_orientation) || isNaN(head_orientation)) throw new Error('NaN')
        // let mp1 = new Vector2(tail.x + Math.cos(tail_orientation)*r, tail.y + Math.sin(tail_orientation)*r)
        // let mp2 = new Vector2(head.x + Math.cos(head_orientation)*r, head.y + Math.sin(head_orientation)*r)
        // let direction = mp2.sub(mp1).normalize()
        // r = Math.min(r,mp1.sub(mp2).length/2)
        // let arcp1 = mp1.add(direction.mulScalar(r))
        // let arcp2 = mp2.sub(direction.mulScalar(r))
        // let a = arcp1.sub(tail).length/2
        // let radius = a*r*1/(Math.sqrt(r**2-a**2))
        // if(isNaN(radius) || direction.dot(head.sub(tail))<0) radius = 0
        // print(tail_orientation,direction.angle())
        // let path = `M ${tail.x} ${tail.y} A ${radius} ${radius} 0 0 ${direction.rotate(tail_orientation).angle()>0 ? 1 : 0} ${arcp1.x} ${arcp1.y} L ${arcp2.x} ${arcp2.y} A ${radius} ${radius} 0 0 ${direction.rotate(head_orientation).angle()>0 ? 1 : 0} ${head.x} ${head.y}`
        // let tangent = mp2.add(head).sub(mp1.add(tail)).normalize()
        // this.pathResult = {
        //     tangent:tangent,
        //     normal:tangent.rotate(Math.PI/2),
        //     length:d
        // }



        // let delta = head.sub(tail)
        // let tangent1 = Vector2.fromPolar(1,tail_orientation)
        // let tangent2 = Vector2.fromPolar(1,head_orientation)
        // let normal1 = tangent1.rotate(Math.PI/2)
        // let normal2 = tangent2.rotate(Math.PI/2)

        // let maxR = Math.min(
        //     delta.length/4/Math.sin(Vector2.angle(normal1,delta)),
        //     delta.length/4/Math.sin(Vector2.angle(normal2,delta))
        // )

        // const r = Math.min(20, Math.abs(maxR))

        // const flip = (Vector2.angle(tangent1,head.sub(tail))>0 ? 1 : -1)

        // let c1 = tail.add(normal1.mulScalar(r*flip))
        // let c2 = head.add(normal2.mulScalar(r*flip))

        // let m = c1.add(c2).mulScalar(0.5)
        // let centerToM = c1.sub(m)
        // let d = centerToM.length
        // let commonTangentDir= centerToM.rotate(Math.asin(r/d)*flip).normalized()

        // let ct1 = m.add(commonTangentDir.mulScalar((d*d-r*r)**0.5))
        // let ct2 = m.sub(commonTangentDir.mulScalar((d*d-r*r)**0.5))
        // let path = `M ${tail.x} ${tail.y} A ${r} ${r} 0 0 ${flip==1?1:0} ${ct1.x} ${ct1.y} L ${ct2.x} ${ct2.y} A ${r} ${r} 0 0 ${flip==1?0:1} ${head.x} ${head.y}`

        // let tangent = commonTangentDir
        // this.pathResult = {
        //     tangent:tangent,
        //     normal:tangent.rotate(Math.PI/2),
        //     length:head.sub(tail).length
        // }

        return path
    }
}

class DotAnimation{
    /*
    * The dot will move along the edge path in a loop
    */
    dot: SVGCircleElement
    stopDelay: number = 300
    stopDelayTimer: NodeJS.Timeout
    stopTime = 0
    animating: boolean = false
    pathResult: PathResult
    lastFrameTime: number = 0
    private progress: number = 0 // 0~1
    constructor(dot: SVGCircleElement){
        this.dot = dot
        this.dot.setAttribute('opacity','0')
    }


    setPathResult(pathResult: PathResult) {
        this.pathResult = pathResult
    }

    start(){
        this.dot.setAttribute('opacity','1')
        if(!this.animating){
            requestAnimationFrame(this.animate.bind(this))
            clearTimeout(this.stopDelayTimer)
            this.animating = true
            this.lastFrameTime = performance.now()
        }
        this.stopTime = 0
    }

    stop(){
        clearTimeout(this.stopDelayTimer)
        this.stopDelayTimer = setTimeout(() => {
            this.animating = false
            this.progress = 0
        }, this.stopDelay);
        this.stopTime = performance.now() + this.stopDelay

        this.dot.setAttribute('opacity','0')
    }

    stopImmediately(){
        clearTimeout(this.stopDelayTimer)
        this.animating = false

        this.dot.setAttribute('opacity','0')
    }

    animate(){
        if(!this.animating) return;
        let now = performance.now()
        let dt = now - this.lastFrameTime

        if(this.stopTime != 0){
            // set opacity to (this.stopTime - now)/this.stopDelay
            let opacity = (this.stopTime - now)/this.stopDelay
            this.dot.setAttribute('opacity',opacity.toString())
        }

        //this.progress += dt/1000*100/this.pathResult.length
        this.progress += dt/400
        if(this.progress > 1) this.progress = 0
        let [tail,mp1,mp2,head] = this.pathResult.points // A bezier curve of 4 points

        let t = this.progress
        let x = (1-t)**3*tail.x + 3*(1-t)**2*t*mp1.x + 3*(1-t)*t**2*mp2.x + t**3*head.x
        let y = (1-t)**3*tail.y + 3*(1-t)**2*t*mp1.y + 3*(1-t)*t**2*mp2.y + t**3*head.y
        this.dot.setAttribute('cx',x.toString())
        this.dot.setAttribute('cy',y.toString())

        requestAnimationFrame(this.animate.bind(this))
        this.lastFrameTime = now
    }
}
