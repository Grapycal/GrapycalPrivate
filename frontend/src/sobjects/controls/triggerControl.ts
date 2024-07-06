import { StringTopic } from "objectsync-client"
import { Control } from "./control";
import { fetchWithCache } from "../../app"

export class TriggerControl extends Control {
    
    button: HTMLInputElement
    line: SVGElement

    protected get template (){return `
    <div class="control flex-horiz control-always-show">
        
        <button class="btn" ref="button"></button>
        <!-- a dotted line connecting the button to the control -->
        <svg ref="line" class="line" width="50" height="10">
            <line stroke-dasharray="4" x1="3" y1="5.5" x2="42" y2="5.5" />
        </svg>
        <div ref="label" class="label only-show-in-normal-node"></div>
    </div>
    `}

    protected get style(){return `
    .btn {
        position: absolute;
        left: -50px;
        display: flex;
        height: 20px;
        align-items: center;
        border-radius: 2px;
        transform: translateX(-100%);
    }
    .line {
        stroke: #777777;
        stroke-width: 4;
        position: absolute;
        left: -50px;
    }
    `}

    label: HTMLDivElement

    protected onStart(): void {
        super.onStart()
        if(this.node.isPreview){
            //hide the button in preview mode
            this.button.style.display = "none"
            this.line.style.display = "none"
        }
        this.link(this.getAttribute('label').onSet, (label) => {
            this.label.innerText = label
        })
        fetchWithCache('svg/task.svg')
            .then(svg => {
                let t = document.createElement('template')
                t.innerHTML = svg
                let svgNode = t.content.firstChild as SVGElement
                svgNode.classList.add('TriggerControl-svg')
                svgNode.setAttribute('width', '12')
                svgNode.setAttribute('height', '12')
                this.button.appendChild(svgNode)
            }
        )
                    
        this.button.addEventListener("click", (e) => {
            this.emit("click")
        })
        this.button.addEventListener("mousedown", (e) => {
            e.stopPropagation()
        })
    }

}