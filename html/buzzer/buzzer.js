var __BUZZER_NUMBER_TO_KEYCODE__ = {
    1: 97,
    2: 98,
    3: 99,
    4: 100,
    5: 101,
    6: 101,
    7: 102,
    8: 103,
    9: 0,
    10: 0,
    11: 0,
    12: 0,
    13: 0,
    14: 0,
    15: 0,
    16: 0,
    17: 0,
    18: 0,
    19: 0,
    20: 0,
    21: 0,
    22: 0,
    23: 0,
    24: 0,
    25: 0
};
/**
 * Convert a keycode to a buzzer number.
 * @param keycode
 */
var k2b = function (keycode) {
    for (var buzzer_num in __BUZZER_NUMBER_TO_KEYCODE__) {
        if (__BUZZER_NUMBER_TO_KEYCODE__[buzzer_num] === keycode) {
            return parseInt(buzzer_num);
        }
    }
    return null;
};
jQuery.fn.center = function () {
    this.css("position", "absolute");
    this.css("top", Math.max(0, (($(window).height() - $(this).outerHeight()) / 2) +
            $(window).scrollTop()) + "px");
    this.css("left", Math.max(0, (($(window).width() - $(this).outerWidth()) / 2) +
            $(window).scrollLeft()) + "px");
    return this;
};

var teams = [
    {
        "name": "Team1",
        "buzzers": [1, 2, 3, 4],
        "keycodes": [97, 98, 99, 100] // a,b,c,d
    },
    {
        "name": "Team2",
        "buzzers": [5, 6, 7, 8],
        "keycodes": [101, 102, 103, 104]
    }
];

var ready_for_buzzers = false;
var buzzed_in_teams = [];

$(document).keypress(function (e) {
    $("#result").text(e.which);

    if (ready_for_buzzers) {

        var team = find_team_with_buzzer(teams, k2b(e.which));

        if (team === null) {
            $("#result").text("Unknown buzzer");
            $("#teamseq").empty();
            buzzed_in_teams.length = 0;  // Clear the array
            ready_for_buzzers = false;
        } else {
            buzzed_in_teams.push(team);
            var new_li = $("<li></li>");
            new_li.text(team.name);
            $("#result").text(team.name);
            $("#teamol").append(new_li);
            $("#teamseq").center();
        }
    }
});

var make_ready_for_buzzers = function () {
    var ts = $("#teamseq");
    ts.find("div.message").text("Ready!");
    ts.center().attr("display", "block");
    ready_for_buzzers = true;
};


var find_team_with_buzzer = function (teams, buzzer_number) {
    var numTeams = teams.length;
    for (var i = 0; i < numTeams; i++) {
        var team = teams[i];
        if (team.buzzers.indexOf(buzzer_number) !== -1) {
            // Found it
            return team;
        }
    }
    return null;
};

var find_team_with_keycode = function (teams, keycode) {
    var numTeams = teams.length;
    for (var i = 0; i < numTeams; i++) {
        var team = teams[i];
        if (team.keycodes.indexOf(keycode) !== -1) {
            // Found it
            return team;
        }
    }
    return null;
};

$(document).ready(function () {

    $("#go").click(function () {
        make_ready_for_buzzers();
        console.log("Go clicked")
    });

});

