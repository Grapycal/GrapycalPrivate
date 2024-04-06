/**
 * This is a template to create a subclass of Componentable
 */
import { Componentable } from "../component/componentable"

export class CompnentableTemplate extends Componentable{

    /* ===== Template ===== */

    // The HTML template for the component.
    protected get template(): string { return `
        <div>
            <!-- Add your html here -->
        </div>
    `}

    /* ===== Style ===== */

    // The CSS style for the component. HTML classes are scoped to the component.
    protected get style(): string { return `
        /* Add your css here */
    `}

    /* ===== Element References ===== */

    // The references to the HTML elements in the template. 
    // For example, to access <div ref="ouo"></div>, type:
    //      private readonly ouo: HTMLDivElement
    // Then, you can use this.ouo to access the element.


    /* ===== Other Properties ===== */

    // Declare other properties you need here.


    /* ===== contructor ===== */

    // The constructor is called when the component is created.
    constructor(){
        super()
    }
}