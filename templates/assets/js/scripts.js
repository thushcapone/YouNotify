
jQuery(document).ready(function() {

    /*
        Background slideshow
    */
    /*$.backstretch([
      "assets/img/backgrounds/1.jpg"
    , "assets/img/backgrounds/2.jpg"
    , "assets/img/backgrounds/3.jpg"
    , "assets/img/backgrounds/fond1.jpg"
    , "assets/img/backgrounds/fond2.jpg"
    , "assets/img/backgrounds/fond3.jpg"
    , "assets/img/backgrounds/fond4.jpg"
    , "assets/img/backgrounds/fond5.jpg"
    ], {duration: 3000, fade: 750});*/

    /*
        Tooltips
    */
    $('.links a.home').tooltip();
    $('.links a.contact').tooltip();
    $('.links a.what').tooltip();

    /*
        Form validation
    */
    $('.register form').submit(function(){
        $(this).find("label[for='firstname']").html('First Name');
        $(this).find("label[for='lastname']").html('Last Name');
        $(this).find("label[for='email']").html('Email');
        $(this).find("label[for='msg']").html('Message');
        ////
        var firstname = $(this).find('input#firstname').val();
        var lastname = $(this).find('input#lastname').val();
        var email = $(this).find('input#email').val();
        var msg = $(this).find('input#msg').val();
        if(firstname == '') {
            $(this).find("label[for='firstname']").append("<span style='display:none' class='red'> - Please enter your first name.</span>");
            $(this).find("label[for='firstname'] span").fadeIn('medium');
            return false;
        }
        if(lastname == '') {
            $(this).find("label[for='lastname']").append("<span style='display:none' class='red'> - Please enter your last name.</span>");
            $(this).find("label[for='lastname'] span").fadeIn('medium');
            return false;
        }
        if(email == '') {
            $(this).find("label[for='email']").append("<span style='display:none' class='red'> - Please enter a valid email.</span>");
            $(this).find("label[for='email'] span").fadeIn('medium');
            return false;
        }
        if(msg == '') {
            $(this).find("label[for='msg']").append("<span style='display:none' class='red'> - Please enter a message.</span>");
            $(this).find("label[for='msg'] span").fadeIn('medium');
            return false;
        }
    });


});


