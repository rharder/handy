console.log("Loaded propchangeobject.js");

/**
 * Class for adding bindable properties to an object.
 *
 * @author Robert Harder
 */
class PropChangeObject {

    constructor() {
        this._properties = {};  // Key: Property Name, Value: prop value
        this._listeners = {};  // Key: Property Name, Value: list of functions to call on change with new value as parameter
//        this._permission = {};  // Key: Property Name, Value: function that returns true if should fire prop change
    }

    addProperty(propName, initialValue){
        Object.defineProperty(this, propName, {
            get: function(){ return this.get(propName);},
            set: function(val){ this.set(propName, val);}
        });
        this[propName] = initialValue;
    }

    set(propName, val){
        let prev = this._properties[propName];
        this._properties[propName] = val;
        if(!(prev === val))  // Only fire if actually a change
            this.firePropertyChange(propName, val, prev);
    }

    setWithoutFiring(propName,val){
        this._properties[propName] = val;
    }

    get(propName){ return this._properties[propName]; }

    addPropertyChangeListener(propName, func, fireNow){
        if(this._listeners[propName] == undefined)
            this._listeners[propName] = [];
        this._listeners[propName].push(func);
        if(Boolean(fireNow))
            func.bind(this)(this.get(propName), undefined, this);
    }

//    _permitFirePropChange(propName, newVal, oldVal){
//        return true;
//    }

    firePropertyChange(propName, val, prev){
        let listeners = this._listeners[propName] || [];
        for( let f of listeners){
            f.bind(this)(val, prev, this);
        }
    }

}   // end class PropChangeObject
