import { StringTopic } from "objectsync-client"
import { Control } from "./control";
import { EventDispatcher } from "../../component/eventDispatcher"

export class KeyboardControl extends Control {
    
    enableButton: HTMLInputElement
    label = this.getAttribute("label", StringTopic)

    private _enabled = false
    private _pressedKeys = new Set<string>()

    protected template = `
    <div class="control flex-horiz">
        <div class="control-label" id="label"></div>
        <button class="control-button full-width" id="button"></button>
    </div>
    `

    protected onStart(): void {
        super.onStart()
        this.enableButton = this.htmlItem.getEl("button")
        // the enableButton toggles the _enabled property
        this.enableButton.addEventListener("click", (e) => {
            this._enabled = !this._enabled
            this.enableButton.innerText = this._enabled ? "Disable" : "Enable"
            if (this._enabled) {
                this.enable()
            } else {
                this.disable()
            }
            this.enableButton.blur() // prevent spacebar from toggling the button
        })
        this.enableButton.innerText = this._enabled ? "Disable" : "Enable"
        this.label.onSet.add((value) => {
            (this.htmlItem.getEl("label") as HTMLDivElement).innerText = value
        })
    }

    protected enable(): void {
        this.link2(document, "keydown", this.onKeydown)
        this.link2(document, "keyup", this.onKeyup)
    }

    protected disable(): void {
        this.unlink2(document, "keydown")
        this.unlink2(document, "keyup")
    }

    protected onKeydown(e: KeyboardEvent): void {
        if (this._pressedKeys.has(e.key)) {
            e.preventDefault()
            return
        }
        this._pressedKeys.add(e.key)
        this.makeRequest("keydown", {key: e.key})
    }

    protected onKeyup(e: KeyboardEvent): void {
        if (!this._pressedKeys.has(e.key)) {
            return
        }
        this._pressedKeys.delete(e.key)
        this.makeRequest("keyup", {key: e.key})
    }

}