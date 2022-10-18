/**
 * Helper class for working with websockets.
 *
 * @author Robert Harder
 */
console.log("Loaded ws.js");


class WS{
    constructor(url){
        this.url = url;
        this.verbose = true;
        this.reconnectDelay = 1000;  // millis
        this.reconnect = true;
        this._socket = null;
    }

    log(msg){ if(this.verbose) console.log(msg); }

    open(){
        if(this._socket == null){
            this.log("Attempting websocket connection to " + this.url);
            this._socket = new WebSocket(this.url);
            this._socket._tempMsgQueue = [];
            var THIS = this;
            this._socket.onopen = function(e){
                let sock = e.target;
                // This is the new send json function for this._socket
                sock.sendJSON = function(obj){ sock.send(JSON.stringify(obj)); };
                do{
                    // Send the queued messages first
                    let x = sock._tempMsgQueue.shift();
                    if( x != undefined ){
                        sock.sendJSON(x);
                    }
                } while( sock._tempMsgQueue.length > 0 )
                THIS.onopen(e);
            };
            this._socket.onclose = function(e){
                THIS._socket = null;
                if(THIS.reconnect){
                    setTimeout(()=>{THIS.open();}, THIS.reconnectDelay);
//                    setTimeout(THIS.open, THIS.reconnectDelay);
                }
                THIS.onclose(e);
            }
            this._socket.onerror = function(e){ THIS.onerror(e); }
            this._socket.onmessage = function(e){ THIS.onmessage(e); }
            // This is used temporarily while the socket is still opening:
            this._socket.sendJSON = function(obj){ THIS._socket._tempMsgQueue.push(obj); }
        }
        return this;
    }   // end open

    onopen(e){ this.log({onopen:e}); };
    onclose(e){ this.log({onclose:e}); };
    onerror(e){this.log({onerror:e})};
    onmessage(e){this.log({onmessage:e})};

    sendJSON(obj){
        this.open();
        this._socket.sendJSON(obj);
    }
}

