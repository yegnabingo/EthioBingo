const grid = document.getElementById("grid");
const timerText = document.getElementById("timer");

let selected = [];
let seconds = 30;

// Demo player info
document.getElementById("username").innerText = "Test Player";
document.getElementById("balance").innerText = "0 ETB";

// ----------------------------
// Pick System
// ----------------------------

let selectedCard = null;
let pickedCount = 0;

const grid = document.getElementById("cardGrid");

for (let i = 1; i <= 200; i++) {

    const card = document.createElement("div");

    card.className = "card-number";

    card.innerText = i;

    card.dataset.number = i;

    card.onclick = () => {

        if (card.classList.contains("taken")) return;

        document.querySelectorAll(".card-number.selected")
            .forEach(c => c.classList.remove("selected"));

        selectedCard = i;

        card.classList.add("selected");

    };

    grid.appendChild(card);

}

document.getElementById("confirmBtn").onclick = async () => {

    if (selectedCard == null){

        alert("Select one card first.");

        return;

    }

    if(pickedCount >= 5){

        alert("Maximum 5 cards reached.");

        return;

    }

    const response = await fetch("/api/cards/pick", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify({
        telegram_id: telegramId,
        card_number: selectedCard
    })
});

const result = await response.json();

if(result.success){

    pickedCount++;

    document
        .querySelector(`[data-number="${selectedCard}"]`)
        .classList.remove("selected");

    document
        .querySelector(`[data-number="${selectedCard}"]`)
        .classList.add("taken");

    alert(
        `Card ${selectedCard} reserved (${pickedCount}/5)`
    );

    selectedCard = null;

}else{

    alert(result.message);

}

// Timer
const timer = setInterval(() => {

    seconds--;

    timerText.innerText = seconds;

    if (seconds <= 0) {

        clearInterval(timer);

        document.getElementById("confirmBtn").disabled = true;

        alert("Pick Phase Finished.\nNext: Bingo Draw");

        // Next screen will be connected here.

    }

},1000);

// Confirm

document.getElementById("confirmBtn").onclick = ()=>{

    if(selected.length==0){

        alert("Select at least one card.");

        return;

    }

// =============================
// Create Bingo Board (1-75)
// =============================

const numberBoard = document.getElementById("numberBoard");

if (numberBoard) {

    for (let n = 1; n <= 75; n++) {

        const ball = document.createElement("div");

        ball.className = "ball";

        ball.id = "ball-" + n;

        ball.innerText = n;

        numberBoard.appendChild(ball);

    }

}
    
    alert(
        "Cards Selected:\n\n"+
        selected.join(", ")
    );

};

// ==========================
// WebSocket Connection
// ==========================

const protocol = location.protocol === "https:" ? "wss" : "ws";

const socket = new WebSocket(
    protocol + "://" + location.host + "/ws"
);

let callCount = 0;

socket.onmessage = function(event){

    const data = JSON.parse(event.data);

    if(data.type !== "ball") return;

    callCount++;

    document.getElementById("callCount").innerText = callCount;

    document
        .getElementById("ball-" + data.number)
        ?.classList.add("called");

};
