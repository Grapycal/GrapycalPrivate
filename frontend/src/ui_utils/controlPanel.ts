import { StringTopic } from "topicsync-client"
import { Componentable } from "../component/componentable"
import { Workspace } from "../sobjects/workspace"
import { as } from "../utils"

export class ControlPanel extends Componentable{
    protected get template(): string {
        return `
        <div class="cont" slot="default">
            <button ref="play">
                <svg width="18" height="20" xmlns="http://www.w3.org/2000/svg" template_id="template_1491">
                    <polygon points="1,19 1,1 17,10" fill="#55ff55" stroke="#008800" stroke-width="2" template_id="template_1491"></polygon>
                </svg>
            </button>
            <button ref="interrupt">
                <svg width="18" height="20" xmlns="http://www.w3.org/2000/svg" template_id="template_1491">
                    <rect x="1" y="1" width="16" height="18" fill="#ff5555" stroke="#880000" stroke-width="2" template_id="template_1491"></rect>
                </svg>
            </button>
            <button ref="pause" id="pause">
                <svg width="18" height="20" xmlns="http://www.w3.org/2000/svg" template_id="template_1491">
                    <rect x="1" y="1" width="5" height="18" fill="#5599ff" stroke="#000088" stroke-width="2" template_id="template_1491"></rect>
                    <rect x="12" y="1" width="5" height="18" fill="#5599ff" stroke="#000088" stroke-width="2" template_id="template_1491"></rect>
                </svg>
            </button>
            <button ref="step">
                <svg width="18" height="20" xmlns="http://www.w3.org/2000/svg" template_id="template_1491">
                    <rect x="14" y="1" width="5" height="18" fill="#ffff55" stroke="#888800" stroke-width="2" template_id="template_1491"></rect>
                    <polygon points="1,19 1,1 13,10" fill="#ffff55" stroke="#888800" stroke-width="2" template_id="template_1491"></polygon>
                </svg>
            </button>
        </div>
        `
    }
    protected get style(): string {
        return`
        .cont{
            position:absolute;
            display:flex;
            flex-direction:row;
            bottom: 40px;
            margin: 0 auto;
            padding: 2px;
            background-color: var(--z2);
            opacity:0.7;
            height: 34px;
            z-index:15;
            left: 50%;
            transform: translate(-50%,-50%);
            border-radius: 10px;
            transition: 0.2s;
        }
        .cont:hover{
            opacity:1;
        }
        `
    }

    private readonly play: HTMLButtonElement
    private readonly interrupt: HTMLButtonElement
    private readonly pause: HTMLButtonElement
    private readonly step: HTMLButtonElement

    constructor(runnerStatusTopic: StringTopic) {
        super()
        this.link2(this.play,'click',()=>{
            Workspace.instance.objectsync.makeRequest('play')
        })
        this.link2(this.interrupt,'click',()=>{
            Workspace.instance.objectsync.makeRequest('interrupt')
        })
        this.link2(this.pause,'click',()=>{
            Workspace.instance.objectsync.makeRequest(runnerStatusTopic.getValue().includes('paused') ? 'resume' : 'pause')
        })
        this.link2(this.step,'click',()=>{
            Workspace.instance.objectsync.makeRequest('step')
        })
        runnerStatusTopic.onSet.add((status: string) => {
            this.play.style.display = status.includes('idle') ? 'block' : 'none'
            this.interrupt.style.display = status.includes('idle') ? 'none' : 'block'
            if(status.includes('running')){
                this.interrupt.classList.add('active')
            }
            else{
                this.interrupt.classList.remove('active')
            }
            if(status.includes('paused')){
                this.pause.classList.add('active')
            }
            else{
                this.pause.classList.remove('active')
            }
            this.step.disabled = !(status.includes('paused') && status.includes('running'))
            console.log('runnerStatusTopic',status)
        })
    }
}