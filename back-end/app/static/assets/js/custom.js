$(document).ready(function () {
    $('#Users').addClass("active current-page");
})

$('#btnUsers').on("click", function () {
    active_element = $(".nav-item.active.current-page").attr('id');
    $('#' + active_element).removeClass("active current-page");
    $("#Users").addClass("active current-page");
    $('#' + 'dv' + active_element).addClass("hide-dv")
    $('#dvUsers').removeClass("hide-dv");
});

$('#btnDiscuss').on("click", function () {
    active_element = $(".nav-item.active.current-page").attr('id');
    $('#' + active_element).removeClass("active current-page");
    $("#Discuss").addClass("active current-page");
    $('#' + 'dv' + active_element).addClass("hide-dv")
    $('#dvDiscuss').removeClass("hide-dv");
});

