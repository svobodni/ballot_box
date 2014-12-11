$(document).ready(function() {
    $(".bo-profile").each(function() {
        var $this = $(this);
        var userid = $this.data("userid");
        $.ajax({
            dataType: "json",
            url: BASE_URL+"registry/people/"+userid+".json",
            success: function(data) {
                var html = "";
                html += '<img class="pull-left" src="'+data.person.photo_url+'" />';
                html += '<div class="pull-left">&nbsp;</div><div class="pull-left">'
                for(var i=0; i<data.person.contacts.length; i++) {
                    var t = data.person.contacts[i].type;
                    var v = data.person.contacts[i].value;
                    if(t == "email") {
                        html += '<a href="mailto:'+v+'"><i class="fa fa-envelope fa-fw"></i> '+v+'</a>';
                    } else if(t == "facebook_page") {
                        html += '<a href="'+v+'"><i class="fa fa-facebook fa-fw"></i> FB stránka</a>';
                    } else if(t == "facebook_profile") {
                        html += '<a href="'+v+'"><i class="fa fa-facebook fa-fw"></i> FB profil</a>';
                    } else if(t == "twitter") {
                        html += '<a href="https://twitter.com/'+v+'"><i class="fa fa-twitter fa-fw"></i> Twitter</a>';
                    } else if(t == "web") {
                        html += '<a href="'+v+'"><i class="fa fa-globe fa-fw"></i> Web</a>';
                    } else if(t == "blog") {
                        html += '<a href="'+v+'"><i class="fa fa-book fa-fw"></i> Blog</a>';
                    } else if(t == "google_plus") {
                        html += '<a href="'+v+'"><i class="fa fa-google-plus fa-fw"></i> Google+</a>';
                    } else if(t == "linked_in") {
                        html += '<a href="'+v+'"><i class="fa fa-linkedin fa-fw"></i> LinkedIn</a>';
                    } else if(t == "phone") {
                        html += '<i class="fa fa-phone fa-fw"></i> '+v;
                    }
                    html += '<br/>'
                }
                if(data.person.cv_url) {
                    html += '<a href="'+data.person.cv_url+'"><i class="fa fa-file-text-o fa-fw"></i> CV</a><br/>';   
                }
                html += "</div>"
                console.log(html);
                $this.html(html);
                console.log(data);

            },
            error: function() {
                $this.html('<i class="fa fa-user fa-5x"></i>');
            }
        });
    });
    if($('.bo-profile').length>0) {
        $('.bo-profile-empty').html('<i class="fa fa-user fa-3x"></i>');
    }
});