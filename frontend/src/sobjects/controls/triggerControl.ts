import { StringTopic } from "objectsync-client"
import { Control } from "./control";
import { fetchWithCache } from "../../app"

export class TriggerControl extends Control {
    
    button: HTMLInputElement

    protected get template (){return `
    <div class="control flex-horiz">
        
        <button class="btn" id="button"></button>
        <!-- a dotted line connecting the button to the control -->
        <svg class="line" width="105" height="10">
            <line stroke-dasharray="4" x1="3" y1="5.5" x2="42" y2="5.5" />
        </svg>
        <div ref="label" class="label"></div>
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
        this.button = this.htmlItem.getEl("button")
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
    }

}