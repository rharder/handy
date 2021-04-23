/**
 * Useful with lambdas and other places where you need a "final" object but need to modify its value,
 * in this case adding some add/subtract math operations that are also threadsafe.
 */
public class MutableLong extends Mutable<Long> {
    private final static long serialVersionUID = -3591626905501757199L;

    public MutableLong() {
        super(0L);
    }

    public MutableLong(long value) {
        super(value);
    }

    /**
     * Adds a long, threadsafe.
     */
    public synchronized void add(long val) {
        super.operate(prev -> prev + val);
    }

    /**
     * Subtracts a long, threadafe.
     */
    public synchronized void subtract(long val) {
        super.operate(prev -> prev - val);
    }

    /**
     * Increments by one, threadsafe.
     */
    public synchronized void increment() {
        super.operate(prev -> prev + 1);
    }

    /**
     * Returns the stored value but also increments the value by one.  The returned value
     * is the value *before* it is incremented.  Threadsafe.
     */
    public synchronized long getThenIncrement() {
        long v = get();
        increment();
        return v;
    }

    /**
     * Returns the stored value but also increments the value by one.  The returned value
     * is the value *after* it is incremented.  Threadsafe.
     */
    public synchronized long incrementThenGet() {
        increment();
        return get();
    }

}
