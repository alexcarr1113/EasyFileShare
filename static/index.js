$(document).ready(function () { // Runs when document is loaded

    $("#login").submit(function (event) { // Send login code
        sessionCode = $("#code_input").val();
        if (sessionCode.length > 0) {
            $.ajax({
                type: "POST",
                url: "/"+sessionCode,
                contentType: 'application/json; charset=utf-8',
                dataType: "json",
                data: JSON.stringify({ "code": sessionCode }),
                success(response) {
                    window.location.replace("/"+sessionCode);
                },
                error(response) {
                    $("#codelabel").html("Invalid Code");
                }
            })
        }
        event.preventDefault();
    })


    $("#uploadfile").on("change", function (event) { // When file is changed, capture file and create form data object
        var file = $("#fileform")[0];
        var formData = new FormData(file);
        $.ajax({ // Send AJAX request
            type: "POST",
            url: "/upload/0",
            data: formData,
            processData: false,
            contentType: false,
            cache: false,
            success: function (response) { // If successful, remove current list and rebuild list with new files
                window.location.replace("/"+response["sessionCode"]); // Redirect to session
            },
            error: function (response) {
                console.log(response);
            }
        })
    })

    $("#textupload").submit(function (event) { // When form is submitted, upload text
        user_text = $("#text_input").val();
        console.log(user_text);
        if (user_text.length > 0) {
            $.ajax({ // Send AJAX request
                type: "POST",
                url: "/upload/0",
                contentType: 'application/json; charset=utf-8',
                dataType: "json",
                data: JSON.stringify({ "user_text": user_text }),
                success: function (response) { // If successful, remove current list and rebuild list with new files
                    window.location.replace("/"+response["sessionCode"]); // Redirect to session
                },
                error: function (response) {
                    console.log(response);
                }
            })
        }
        else {
            $("#text_label").html("No text entered");
        }
        event.preventDefault();
    })
})