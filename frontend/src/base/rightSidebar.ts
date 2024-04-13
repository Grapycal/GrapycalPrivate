import { Componentable } from "../component/componentable"
import { NodeInspector } from "../ui_utils/nodeInspector"

export class RightSideBar extends Componentable{

    /* ===== Template ===== */

    // The HTML template for the component.
    protected get template(): string { return `
        <div ref="base" class="sidebar sidebar-right">
          <button class="sidebar-collapse-right" id="sidebar-collapse-right">&gt</button>
          <div class="sidebar-container" slot="NodeInspector"></div>
          <div ref="handle" class="sidebar-resize-handle"></div>
        </div>
    `}

    // The CSS style for the component. HTML classes are scoped to the component.
    protected get style(): string { return `
        /* Add your css here */
    `}

    /* ===== Element References ===== */

    private readonly base: HTMLDivElement
    private readonly handle: HTMLDivElement

    
    /* ===== Other Properties ===== */

    // Declare other properties you need below.


    /* ===== contructor ===== */

    // The constructor is called when the component is created.
    constructor(){
        super()

        new NodeInspector(this.htmlItem).mount(this)
        let desiredWidth: number = null;
        let prevX: number = null;
        
        const MIN_WIDTH = 10;
        const MAX_WIDTH = 500;
        const resizeSidebar = (event: MouseEvent)=>{
            event.preventDefault(); // prevents selecting text
            if (desiredWidth != null && this.base) {
                desiredWidth -= event.x - prevX;
                prevX = event.x;
                let newWidth = desiredWidth;
                // check if new width is within bounds
                if (newWidth < MIN_WIDTH) {
                    newWidth = MIN_WIDTH;
                } else if (newWidth > MAX_WIDTH) {
                    newWidth = MAX_WIDTH;
                }
                this.base.style.width = newWidth + 'px';
            }
          }
        
        if (this.base){
            this.link2(this.handle, 'mousedown', (event: MouseEvent)=> {
                desiredWidth = this.base.offsetWidth;
                prevX = event.x;
                document.addEventListener('mousemove', resizeSidebar, false);
            }, false)
        
            document.addEventListener('mouseup', function(event: MouseEvent) {
                desiredWidth = undefined;
                document.removeEventListener('mousemove', resizeSidebar, false);
            }, false);
        }
    }
}