var sessionCode;
var password = 0;

function update_files(fileList) { // Clears file list and rebuild
    $(".file").remove();
    for (var i = 0; i < fileList.length; i++) {
        var filename = fileList[i][0];
        $("#files").append("<div class='row mb-1 file'><div class='col col-md-6'>" + filename + "</div><div class='col col-md-6'><button onclick=download_file('" + filename + "') class='btn btn-outline-primary mx-1'>Download</button><button onclick=remove_file('" + filename + "') class='btn btn-outline-danger mx-1'>Remove</button></div></div>");
    }
}

function update_text(userText) { // Update text field with parameter
    $("#textInput").attr("value", userText);
}

function download_file(filename) {
    var anchor = document.createElement('a');
    anchor.href = "/" + sessionCode + "/" + filename + "/" + password;
    anchor.download = filename;
    console.log("downloading " + filename);
    anchor.click();
}

function remove_file(filename) { // Sends request to remove file from server
    console.log(sessionCode);
    $.ajax({
        type: "POST",
        url: "/remove/" + sessionCode + "/" + filename,
        success: function (response) {
            update_files(response["fileList"]);
        },
        error: function (error) {
            console.log(error);
        }
    })
}

async function copy_text(text) {
    try {
        await navigator.clipboard.writeText(text);
    }
    catch (err) {
        console.log(err);
    }
}

$(document).ready(function () { // Runs when document is loaded

    // Send ajax request for files and text
    sessionCode = $("#sessioncode").html();
    $.ajax({
        type: "POST",
        url: "/" + sessionCode,
        success: function (response) {
            update_files(response["fileList"]);
            update_text(response["userText"]);
        },
        error: function (error) {
            console.log(error);
        }
    })

    // Sets password variable when field changed
    $("#encryptionKey").on("change", function (event) {
        password = $("#encryptionKey").val();
        if (password == "") {
            password = 0;
        }
    })

    $("#uploadtext").submit(function (event) { // Copies text in upload field to clipboard when button clicked
        event.preventDefault();
        var copyText = document.getElementById("textInput");
        copyText.select();
        copyText.setSelectionRange(0, 99999);
        copy_text(copyText.value);
    })

    $("#uploadtext").on("focusout", function (event) { // Send text field to server
        user_text = $("#textInput").val();
        $.ajax({ // Send AJAX request
            type: "POST",
            url: "/upload/" + sessionCode,
            contentType: 'application/json; charset=utf-8',
            dataType: "json",
            data: JSON.stringify({ "user_text": user_text }),
            success: function (response) { // If successful replace field value with text
                update_text(response["userText"]);
            },
            error: function (response) {
                console.log(response);
            }
        })
        event.preventDefault();
    })

    $("#uploadfile").on("change", function (event) { // When form is submitted, capture file and create form data object
        var file = $("#fileform")[0];
        var formData = new FormData(file);
        $.ajax({ // Send AJAX request
            type: "POST",
            url: "/upload/" + sessionCode + "/" + password,
            data: formData,
            processData: false,
            contentType: false,
            cache: false,
            success: function (response) { // If successful, remove current list and rebuild list with new files
                update_files(response["fileList"]);
                $("#uploadfile").val('');
            },
            error: function (response) {
                console.log(response);
            }
        })
        event.preventDefault();
    })
})