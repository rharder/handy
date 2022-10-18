console.log("Loaded main.js");
var ws;  // Will be the websocket object WS

document.addEventListener("DOMContentLoaded", function(event) {

    // Connect to the websocket
    let wsUri = ((window.location.protocol === "https:") ? "wss://" : "ws://") + window.location.host + "/ws";
    console.log("Opening websocket " + wsUri);
    ws = new WS(wsUri);
    ws.onmessage = function(e){ws_onmessage(e);};
    ws.onopen = function(e){ws_onopen(e);};
    ws.onclose = function(e){ws_onclose(e);};
    ws.open();

});

function ws_onopen(e){
    console.log("A new websocket opened: " + JSON.stringify(e));
}
function ws_onclose(e){
    console.log("A websocket closed: " + JSON.stringify(e));
}

function ws_onmessage(e){

    try {
        var wsMsg = JSON.parse(e.data);
    } catch(err) {
        console.log(err);
        console.log(e.data);
        return;
    }
    console.log("A new websocket message arrived: " + JSON.stringify(wsMsg));
    if(wsMsg.replacementText != undefined){
        let text = wsMsg.replacementText;
        console.log("Replace text with: " + text);
        document.getElementById("ws-output").textContent = text;
    }
}

function updateLiveWebsocketInput(evt){
    let text = document.getElementById("ws-input").value.trim();
    ws.sendJSON({"userInput":text});
}


