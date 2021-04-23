import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;

/**
 * A generic used in several places to represent two pieces of data with a timestamp attached.
 */
public class TimestampedTupleTwo<A, B> implements Serializable, Comparable<TimestampedTupleTwo<?, ?>>, Cloneable {
    private final static long serialVersionUID = 859865928593408875L;

    public final Instant timestamp;
    public final A a;
    public final B b;


    public TimestampedTupleTwo(A a, B b, Instant timestamp) {
        this.a = a;
        this.b = b;
        this.timestamp = Objects.requireNonNull(timestamp);
    }

    public TimestampedTupleTwo(TimestampedData<A> td, B b) {
        this.a = td.get();
        this.b = b;
        this.timestamp = td.getTimestamp();
    }

    public A getA() {
        return a;
    }

    public B getB() {
        return b;
    }


    public Instant getTimestamp() {
        return timestamp;
    }

    public TimestampedTupleTwo<A, B> byReplacingA(A a) {
        return new TimestampedTupleTwo<>(a, getB(), getTimestamp());
    }

    public TimestampedTupleTwo<A, B> byReplacingB(B b) {
        return new TimestampedTupleTwo<>(getA(), b, getTimestamp());
    }

    public TimestampedTupleTwo<A, B> byReplacingTimestamp(Instant timestamp) {
        return new TimestampedTupleTwo<>(getA(), getB(), timestamp);
    }

    /**
     * Returns a shallow clone of the tuple
     */
    @SuppressWarnings("unchecked")
    @Override
    public TimestampedTupleTwo<A, B> clone() {
        try {
            return (TimestampedTupleTwo<A, B>) super.clone();
        } catch (CloneNotSupportedException e) {
            e.printStackTrace();
        }
        assert false : "This object is in fact cloneable.";
        return null;
    }


    @Override
    public int hashCode() {
        A a = getA();
        B b = getB();
        Instant t = getTimestamp();
        long result = (a == null ? 0 : a.hashCode()) +
                (b == null ? 0 : b.hashCode()) +
                (t == null ? 0 : t.hashCode());
        return (int) (result % Integer.MAX_VALUE);
    }

    @Override
    public boolean equals(Object o) {

        // If the object is compared with itself then return true
        if (o == this) {
            return true;
        }

        if (!(o instanceof TimestampedTupleTwo)) {
            return false;
        }

        // typecast o to TimestampedData so that we can compare data members
        TimestampedTupleTwo<?, ?> other = (TimestampedTupleTwo<?, ?>) o;

        // Compare the data members and return accordingly
        return Objects.equals(getA(), other.getA()) &&
                Objects.equals(getB(), other.getB()) &&
                Objects.equals(getTimestamp(), other.getTimestamp());
    }

    @Override
    public int compareTo(TimestampedTupleTwo o) {
        return this.timestamp.compareTo(o.timestamp);
    }
}
