function foo(x) {
        return Object.is(Math.expm1(x), -0);
}

foo(0);
for(let i = 0; i < 100000; i++)
    console.log(foo(-0));
