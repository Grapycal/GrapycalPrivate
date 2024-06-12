import { Componentable } from "../component/componentable"

export class PieChart extends Componentable{
    protected get template(): string{
        return `
            <div ref="base" class="flex-horiz">
                <div ref="name" class="name"></div>
                <div ref="pie" class="pie"></div>
            </div>
            `;
    }

    protected get style(): string{
        return `   
            .name{
                margin-right: 10px;
            }
            .pie{
                background-image: conic-gradient(orange 64%, blue 64%, blue 81%, black 81%);
                border-radius: 50%;
            }
            `;
    }

    base: HTMLDivElement;
    name: HTMLDivElement;
    pie: HTMLDivElement;

    constructor(width:number, height:number, name?:string){
        super();
        this.pie.style.width = width + "px";
        this.pie.style.height = height + "px";
        if(name){
            this.name.innerText = name;
        }
    }

    set_data(data: number[]){
        let sum = data.reduce((a, b) => a + b, 0);
        let colors = ["red", "blue", "green", "yellow", "orange", "purple", "pink", "brown", "gray", "black"];
        let str = "conic-gradient(";
        let start = 0;
        for(let i = 0; i < data.length; i++){
            let end = start + data[i] / sum * 100;
            str += colors[i] + " " + start + "%, " + colors[i] + " " + end + "%";
            if(i < data.length - 1){
                str += ", ";
            }
            start = end;
        }
        str += ")";
        this.pie.style.backgroundImage = str;
    }

    set_description(description: string){
        this.base.title = description;
    }

    set_name(name: string){
        this.name.innerText = name;
    }

    hide(){
        this.base.style.display = "none";
    }

    show(){
        this.base.style.display = "flex";
    }
        
}