/**
 * This is a template to create a subclass of CompSObject.
 */
import { CompSObject } from "../sobjects/compSObject"

export class CompSobjectTemplate extends CompSObject{

    /* ===== Get Attributes ===== */

    // Get attributes provided by the backend to communicate with the backend. For example:
    //     private readonly display_name = this.getAttribute('display_name', StringTopic)
    

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


    /* ===== onStart ===== */

    // The onStart method is called when the sobject is created and the attributes are initialized.
    protected onStart(): void {
        super.onStart()
        
    }
}