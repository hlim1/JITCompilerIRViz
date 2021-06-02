function crash() {
    let confused;
    for (a=0;a<2;a++) {
        for (let i = -0.0; i < 100; i++) {
            confused = Math.max(-1, i);
            console.log(Object.is(confused, -0));
        }
    }
}

%PrepareFunctionForOptimization(crash);
(crash());
%OptimizeFunctionOnNextCall(crash);
(crash());
