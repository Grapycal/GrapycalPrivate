
export class SoundManager {
    click: HTMLAudioElement;
    constructor() {
        this.click = new Audio("click1.mp3");
        this.click.volume = 1;
    }
    playClick() {
        this.click.currentTime = 0;
        this.click.play()
    }
}