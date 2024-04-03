import { DictTopic, FloatTopic, SObject, StringTopic } from "objectsync-client"
import { Control } from "./control";
import { print } from "../../devUtils"
import { Edge } from "../edge"
import { Port } from "../port"

export class SliderControl extends Control {
    
    slider: HTMLInputElement
    numberInput: HTMLInputElement
    label = this.getAttribute("label", StringTopic)
    value = this.getAttribute("value", FloatTopic)
    config = this.getAttribute("config", DictTopic<string, any>)

    protected template = `
    <div class="control flex-horiz">
        <div class="control-label" id="label"></div>
        <div class="control-slider-container">
            <input type="range" class="control-slider full-width" id="slider" />
            <input type="number" class="control-input" id="input" />
        </div>
    </div>
    `

    protected css = `
    .control-slider-container{
        position: relative;
        flex-grow: 1;
        height: 15px;
    }
    .control-input {
        position: absolute;
        width: 100%;
        height: 100%;
    }
    .control-slider {
        position: absolute;
        width: 100%;
        height: 100%;
    }
    `

    get min(): number {
        return this.config.get("min")
    }

    get max(): number {
        return this.config.get("max")
    }

    get step(): number {
        return this.config.get("step")
    }

    protected onStart(): void {
        super.onStart()
        this.slider = this.htmlItem.getEl("slider")

        this.numberInput = this.htmlItem.getEl("input")
        this.link2(this.slider, "mousedown", (e) => {
            e.stopPropagation()
        })
        this.link2(this.numberInput, "mousedown", (e) => {
            e.stopPropagation()
        })
        this.link(this.label.onSet, (label) => {
            this.htmlItem.getEl("label").textContent = label
        })
        this.link(this.config.onSet, (mode) => {
            this.slider.min = mode.min
            this.slider.max = mode.max
            this.slider.step = mode.step
        })
        this.slider.min = this.config.get('min')
        this.slider.max = this.config.get('max')
        this.slider.step = this.config.get('step')

        this.link(this.value.onSet, (value) => {
            this.slider.value = value
            this.numberInput.value = value
            this.slider.style.backgroundImage = `linear-gradient(to right, #007bff 0%, #007bff ${((value - this.min) / (this.max - this.min)) * 100}%, #ccc ${((value - this.min) / (this.max - this.min)) * 100}%, #ccc 100%)`
        })
        this.link2(this.slider,"input", (e) => {
            if (this.config.get('int_mode')) {
                this.value.set(parseInt(this.slider.value))
            } else {
                this.value.set(parseFloat(this.slider.value))
            }
        })
        this.link2(this.numberInput,"blur", (e) => {
            if (this.config.get('int_mode')) {
                this.value.set(parseInt(this.numberInput.value))
            } else {
                this.value.set(parseFloat(this.numberInput.value))
            }
        })
    }

}