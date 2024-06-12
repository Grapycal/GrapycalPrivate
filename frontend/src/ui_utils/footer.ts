import { DictTopic, EventTopic } from "objectsync-client"
import { Componentable } from "../component/componentable"
import { EventDispatcher } from "../component/eventDispatcher"
import { print } from "../devUtils"
import { Workspace } from "../sobjects/workspace"
import { Vector2, textToHtml } from "../utils"
import { LIB_VERSION } from '../version';
import { PieChart } from "./pieChart"

enum ClientMsgTypes{
    STATUS='status',
    NOTIFICATION='notification'
}

type Message = {
    message:string,
    type:ClientMsgTypes
}
function formatBytes(bytes: number, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
export class Footer extends Componentable{
    static ins: Footer
    static setStatus(status: string){
        Footer.ins.setStatus(status);
    }
    protected get template(): string{
        return `
            <div class="footer">
                <div id="extend-area"></div>
                <div id="bar">
                    <div class="flex-horiz cont">
                        <span id="workspace-name"></span>
                        <span id="status"></span>
                    </div>
                    <div class="flex-horiz cont">
                        <div class="flex-horiz pie" slot="PieChart"></div>
                        <span class="version">Grapycal v${LIB_VERSION}</span>
                    </div>
                </div>
            </div>
            `;
        }

    protected get style(): string{
        return `
        
            #bar{
                justify-content: space-between;
                white-space: nowrap;
                position: relative;
                padding: 0 30px;
                display: flex;
                align-items: 
                bottom: 0;
                height: 24px;
                gap: 50px;
                user-select: none;
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                cursor: ns-resize;
            }
            .cont{
                gap: 50px;
            }   
            .float-left{
                margin-left: auto;
            }
            #status{
                overflow: hidden;
                flex-shrink: 1;
            }
            #extend-area{
                overflow: auto;
                position: relative;
                bottom: 0;
                top: 0;
                height: 0;
                background-color: var(--z0);
                flex-shrink: 1;
                padding: 0 30px;
            }
            .version{
                color: var(--text-low);
                flex-shrink: 0;
            }
            .pie{
                gap: 20px;
                color: var(--text-low);
            }
            `;
        }

    workspaceName: HTMLSpanElement
    status: HTMLSpanElement
    bar: HTMLDivElement
    extendArea: HTMLDivElement
    displacement: number = 0;
    constructor(){
        super();
        Footer.ins = this;
        this.workspaceName = this.htmlItem.getEl('workspace-name', HTMLSpanElement);
        this.status = this.htmlItem.getEl('status', HTMLSpanElement);
        this.bar = this.htmlItem.getEl('bar', HTMLDivElement);
        this.extendArea = this.htmlItem.getEl('extend-area', HTMLDivElement);

        this.status.innerHTML = 'Loading workspace...';

        this.workspaceName.innerHTML = 'workspace.grapycal';

        this.link(this.eventDispatcher.onDrag,this.onDrag);
        this.link(this.eventDispatcher.onDragEnd,this.onDragEnd)
        ;
        Workspace.instance.objectsync.on(`status_message`, (msg:Message)=>{
            if(msg.type==ClientMsgTypes.STATUS)
                this.setStatus(msg.message);
        });
        Workspace.instance.objectsync.on(`status_message_${Workspace.instance.objectsync.clientId}`, (msg:Message)=>{
            if(msg.type==ClientMsgTypes.STATUS)
                this.setStatus(msg.message);
        });
        Workspace.instance.objectsync.getTopic('meta',DictTopic<string,any>).onSet.add((value)=>{
            this.workspaceName.innerHTML = value.get('workspace name');
            // title
            let fileName = value.get('workspace name').split('/').pop().split('.')[0];
            document.title = `${fileName} - Grapycal`;
        })

        const cpu_pie = new PieChart(20,20,'CPU').mount(this);
        const ram_pie = new PieChart(20,20,'RAM').mount(this);
        const gpu_mem_pie = new PieChart(20,20,'GPU Mem').mount(this);

        Workspace.instance.objectsync.getTopic('os_stat',DictTopic<string,any>).onSet.add((value)=>{
            cpu_pie.set_data([value.get('cpu').this, value.get('cpu').other, value.get('cpu').remain]);

            // .2f
            cpu_pie.set_description(`CPU: Grapycal ${value.get('cpu').this.toFixed(2)}%, other ${value.get('cpu').other.toFixed(2)}%, remain ${value.get('cpu').remain.toFixed(2)}%`);
            cpu_pie.set_name('CPU ' + value.get('cpu').this.toFixed(2) + '%');

            ram_pie.set_data([value.get('ram').this, value.get('ram').other, value.get('ram').remain]);

            ram_pie.set_description(`RAM: Grapycal ${formatBytes(value.get('ram').this)}, other ${formatBytes(value.get('ram').other)}, remain ${formatBytes(value.get('ram').remain)}`);
            ram_pie.set_name('RAM ' + formatBytes(value.get('ram').this));
            if(value.has('gpu_mem')){
                gpu_mem_pie.set_data([value.get('gpu_mem').this, value.get('gpu_mem').other, value.get('gpu_mem').remain]);
                gpu_mem_pie.set_description(`GPU Mem: Grapycal ${formatBytes(value.get('gpu_mem').this)}, other ${formatBytes(value.get('gpu_mem').other)}, remain ${formatBytes(value.get('gpu_mem').remain)}`);
                gpu_mem_pie.set_name('GPU Mem ' + formatBytes(value.get('gpu_mem').this));
            }else{
                gpu_mem_pie.hide();
            }
        })
    }

    setStatus(status: string){
        this.status.innerHTML = status;
        const p = document.createElement('p');
        p.innerHTML = textToHtml(status);
        this.extendArea.append(p);
    }

    onDrag(event: DragEvent, from:Vector2, to:Vector2){
        this.displacement += to.y - from.y;
        let realDisplacement = Math.max(0, this.displacement);
        realDisplacement = Math.min(realDisplacement, 400);
        this.extendArea.style.height = `${realDisplacement}px`;
    }

    onDragEnd(event: DragEvent){
        let realDisplacement = Math.max(0, this.displacement);
        realDisplacement = Math.min(realDisplacement, 400);
        this.displacement = realDisplacement;
        
    }
}