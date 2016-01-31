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
                try {
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
                            if (!/^https?:\/\//i.test(v)) {
                                v = 'https://twitter.com/' + v;
                            }
                            html += '<a href="'+v+'"><i class="fa fa-twitter fa-fw"></i> Twitter</a>';
                        } else if(t == "web") {
                            if (!/^https?:\/\//i.test(v)) {
                                v = 'http://' + v;
                            }
                            html += '<a href="'+v+'"><i class="fa fa-globe fa-fw"></i> Web</a>';
                        } else if(t == "forum") {
                            if (!/^https?:\/\//i.test(v)) {
                                v = 'http://' + v;
                            }
                            html += '<a href="'+v+'"><i class="fa fa-users fa-fw"></i> Fórum - kandidátské vlákno</a>';
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
                } catch (e) {
                    console.error("Chyba při zobrazování kontaktu.");
                    console.error(e);
                    console.error(data);
                }
                html += "</div>"
                $this.html(html);

            },
            error: function() {
                $this.html('<i class="fa fa-user fa-5x"></i>');
            }
        });
    });
    if($('.bo-profile').length>0) {
        $('.bo-profile-empty').html('<i class="fa fa-user fa-3x"></i>');
    }
    $.datetimepicker.setLocale('cs');
    $('input[type=datetime]').datetimepicker({
        format: 'Y-m-d H:i:s',
        dayOfWeekStart: 1
    });

    $('.send-announcement').on('click', function(e) {
        if (!confirm('Opravdu chcete rozeslat výsledek volby e-mailem?')) {
            e.preventDefault();
        }
    });
});
