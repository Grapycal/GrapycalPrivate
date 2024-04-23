import { as } from "../utils"

export class SoundManager {
    click: HTMLAudioElement;
    constructor() {
        this.click = new Audio("click1.mp3");
        this.click.volume = 1;
    }
    playClick() {
        let tmp = as(this.click.cloneNode(true),HTMLAudioElement)
        tmp.volume = 1;
        tmp.play()
    }
}