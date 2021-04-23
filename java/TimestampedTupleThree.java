import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;

/**
 * A generic used in several places to represent three pieces of data with a timestamp attached.
 *
 * @see TimestampedData
 * @see TimestampedTupleTwo
 */
public class TimestampedTupleThree<A, B, C> implements Serializable, Comparable<TimestampedTupleThree<?, ?, ?>> {
    private final static long serialVersionUID = 859865928593408875L;

    public final Instant timestamp;
    public final A a;
    public final B b;
    public final C c;


    public TimestampedTupleThree(A a, B b, C c, Instant timestamp) {
        this.a = a;
        this.b = b;
        this.c = c;
        this.timestamp = Objects.requireNonNull(timestamp);
    }

    public A getA() {
        return a;
    }

    public B getB() {
        return b;
    }

    public C getC() {
        return c;
    }


    public Instant getTimestamp() {
        return timestamp;
    }


    public TimestampedTupleThree<A, B, C> byReplacingA(A a) {
        return new TimestampedTupleThree<A, B, C>(a, getB(), getC(), getTimestamp());
    }

    public TimestampedTupleThree<A, B, C> byReplacingB(B b) {
        return new TimestampedTupleThree<>(getA(), b, getC(), getTimestamp());
    }

    public TimestampedTupleThree<A, B, C> byReplacingC(C c) {
        return new TimestampedTupleThree<>(getA(), getB(), c, getTimestamp());
    }

    public TimestampedTupleThree<A, B, C> byReplacingTimestamp(Instant timestamp) {
        return new TimestampedTupleThree<>(getA(), getB(), getC(), timestamp);
    }

    @Override
    public int hashCode() {
        A a = getA();
        B b = getB();
        C c = getC();
        Instant t = getTimestamp();
        long result = (a == null ? 0 : a.hashCode()) +
                (b == null ? 0 : b.hashCode()) +
                (c == null ? 0 : c.hashCode()) +
                (t == null ? 0 : t.hashCode());
        return (int) (result % Integer.MAX_VALUE);
    }

    @Override
    public boolean equals(Object o) {

        // If the object is compared with itself then return true
        if (o == this) {
            return true;
        }

        if (!(o instanceof TimestampedTupleThree)) {
            return false;
        }

        // typecast o to TimestampedData so that we can compare data members
        TimestampedTupleThree<?, ?, ?> other = (TimestampedTupleThree<?, ?, ?>) o;

        // Compare the data members and return accordingly
        return Objects.equals(getA(), other.getA()) &&
                Objects.equals(getB(), other.getB()) &&
                Objects.equals(getC(), other.getC()) &&
                Objects.equals(getTimestamp(), other.getTimestamp());
    }

    @Override
    public int compareTo(TimestampedTupleThree o) {
        return this.timestamp.compareTo(o.timestamp);
    }
}
