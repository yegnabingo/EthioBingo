const grid = document.getElementById("grid");
const timerText = document.getElementById("timer");

let selected = [];
let seconds = 30;

// Demo player info
document.getElementById("username").innerText = "Test Player";
document.getElementById("balance").innerText = "0 ETB";

// Create cards 1-200
for (let i = 1; i <= 200; i++) {

    const btn = document.createElement("button");

    btn.className = "cardBtn";

    btn.innerText = i;

    btn.dataset.id = i;

    btn.onclick = () => {

        if (btn.classList.contains("locked"))
            return;

        if (btn.classList.contains("selected")) {

            btn.classList.remove("selected");

            selected = selected.filter(x => x != i);

            return;
        }

        if (selected.length >= 5) {

            alert("Maximum 5 cards.");

            return;
        }

        btn.classList.add("selected");

        selected.push(i);

    };

    grid.appendChild(btn);

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

    alert(
        "Cards Selected:\n\n"+
        selected.join(", ")
    );

};
