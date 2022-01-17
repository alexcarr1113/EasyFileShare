$(document).ready(function () { // Runs when document is loaded

    $("#login").submit(function (event) { // Send login code when button pressed
        sessionCode = $("#code_input").val();
        if (sessionCode.length > 0) {
            $.ajax({
                type: "POST",
                url: "/"+sessionCode,
                contentType: 'application/json; charset=utf-8',
                dataType: "json",
                data: JSON.stringify({ "code": sessionCode }),
                success() {
                    window.location.replace("/"+sessionCode);
                },
                error() {
                    $("#codelabel").html("Invalid Code");
                }
            })
        }
        event.preventDefault();
    })

    $("#lifetime").on("input", function (event) {
        $("#lifetime_val").html($("#lifetime").val() + " minutes");
    })
})