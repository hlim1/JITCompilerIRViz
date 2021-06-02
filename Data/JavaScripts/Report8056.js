const iarr = [,3];

function includes(arr, val) {
      return arr.includes(val);
}

iarr.__proto__ = [2];

// get feedback
for (var i = 0; i < 10000; i++) {
    print (includes(iarr, 0)); // false
    print (includes(iarr, 2)); // true
}
