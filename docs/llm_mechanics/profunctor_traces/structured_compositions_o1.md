# Exploring Function Composition with Structured Data Types

Function composition is a cornerstone of functional programming, enabling developers to build complex operations by combining simpler functions. While composing functions with basic types is straightforward, dealing with structured or nested data types introduces additional complexity. This exploration delves deep into the theoretical and practical aspects of function composition with structured data types, touching on category theory, type theory, optics, and parallelization techniques in functional programming.

## Table of Contents

1. **Understanding the Challenge**
   - Simple Function Composition
   - Complexity with Structured Data
2. **Theoretical Approaches**
   - a) Lens-based Composition
   - b) Product Categories
   - c) Profunctor Optics
   - d) Monoidal and Applicative Composition
   - e) Monad Transformers
3. **Practical Implementation Patterns**
   - Structured Data Composition Patterns
   - Maintaining Type Safety
   - Performance Considerations
4. **Parallelization over Subfields or List-like Attributes**
   - Applicative Functors for Parallelism
   - Traversals and Mapping
   - Concurrency in Functional Programming
   - Understanding Evaluation Strategies
5. **Deep Dive into Theoretical Concepts**
   - Categorical View
   - Functorial Properties
   - Optic Theory
   - Monads and Applicatives
6. **Translating Concepts into Practical Code**
   - Composing Functions with Lenses
   - Using Profunctor Optics
   - Functorial Mapping over Structured Types
   - Monadic Composition
7. **Conclusion**
8. **References**

---

## 1. Understanding the Challenge

### Simple Function Composition

In functional programming languages like Haskell, composing functions with simple types is straightforward:

```haskell
f :: B -> C
g :: A -> B
h :: A -> C
h = f . g  -- Composition of f and g
```

Here, `h` is a function that takes an input of type `A` and returns an output of type `C` by applying `g` to `A` to get `B`, and then `f` to `B` to get `C`.

### Complexity with Structured Data

When dealing with structured or nested data types (e.g., records, tuples, or custom data structures), the types become more complex:

```haskell
f :: { x :: B1, y :: B2 } -> C
g :: A -> { x :: B1, y :: B2 }
```

Now, `f` expects a record with fields `x` and `y`, and `g` produces such a record from `A`. Directly composing `f` and `g` using `(f . g)` isn't as straightforward because `f` operates on a structured input, and we need to manage the fields appropriately during composition.

**Challenges:**

- **Type Complexity:** Managing functions that operate on complex types with multiple fields.
- **Field Access and Updates:** Accessing and updating specific fields within nested structures.
- **Composition Laws:** Ensuring that the composition adheres to associativity and identity laws.
- **Type Safety:** Maintaining strong type guarantees throughout the composition.

---

## 2. Theoretical Approaches

To address these challenges, we explore several theoretical frameworks:

### a) Lens-based Composition

**Lenses** are abstractions that allow us to focus on a part of a data structure, providing a way to view and update that part in a functional way.

#### Lens Definition

A lens can be defined as:

```haskell
type Lens s t a b = forall f. Functor f => (a -> f b) -> s -> f t
```

- `s`: Source type.
- `t`: Target type after the update.
- `a`: Focused part type (before update).
- `b`: Focused part type (after update).

#### Lens Operations

- **View (Get):** Retrieve the focused part from a structure.
- **Set (Put):** Replace the focused part with a new value.
- **Over (Modify):** Apply a function to the focused part.

#### Composability

Lenses can be composed using function composition `(.)`, allowing us to focus on nested parts of data structures.

#### Benefits

- **Immutable Updates:** Update immutable data structures in a functional way.
- **Modularity:** Break down complex data manipulations into composable parts.
- **Reusability:** Reuse lenses across different functions and modules.

#### Example

Suppose we have nested data types:

```haskell
data Engine = Engine { _horsepower :: Int, _type :: String }
data Car = Car { _make :: String, _model :: String, _engine :: Engine }
```

We can define lenses to focus on the `_horsepower` field within `Engine` inside `Car`:

```haskell
import Control.Lens

makeLens :: Lens' Car String
makeLens = lens _make (\car newMake -> car { _make = newMake })

engineLens :: Lens' Car Engine
engineLens = lens _engine (\car newEngine -> car { _engine = newEngine })

horsepowerLens :: Lens' Engine Int
horsepowerLens = lens _horsepower (\engine newHP -> engine { _horsepower = newHP })

carHorsepowerLens :: Lens' Car Int
carHorsepowerLens = engineLens . horsepowerLens
```

Now, we can use `carHorsepowerLens` to get or set the horsepower of a car:

```haskell
-- Getting the horsepower
getHP :: Car -> Int
getHP = view carHorsepowerLens

-- Setting the horsepower
setHP :: Int -> Car -> Car
setHP newHP = set carHorsepowerLens newHP

-- Modifying the horsepower
increaseHP :: Int -> Car -> Car
increaseHP delta = over carHorsepowerLens (+ delta)
```

### b) Product Categories

Product categories offer a mathematical framework for modeling and manipulating structured data types in functional programming. In category theory, the product of two objects represents a combination that encapsulates both objects while preserving their individual identities. This concept is directly applicable to programming when dealing with data structures like tuples and records.

#### Key Concepts

- **Objects:** In programming, objects correspond to types. This includes basic types (like integers and strings) and structured types (such as tuples, records, or custom data structures).

- **Morphisms:** Morphisms are functions or mappings between types. They represent transformations from one type to another.

- **Product Structure:** The product of two objects A and B is another object A × B, equipped with projection morphisms. In programming terms, this is similar to creating a tuple (A, B) or a record containing fields of types A and B.

#### Composition in Product Categories

When composing functions over structured types, we must account for the structure of the data:

- **Projection Morphisms:** Functions that extract individual components from a structured type. For a tuple (A, B), the projections are functions `fst :: (A, B) -> A` and `snd :: (A, B) -> B`.

- **Injection Morphisms:** Functions that create a structured type from its components. For example, the pairing function `pair :: A -> B -> (A, B)` takes values of types A and B and returns a tuple (A, B).

- **Parallel Composition:** Functions can be composed in parallel over the components of a structured type. This is often represented using operators that apply functions to each component independently.

#### Example

Consider two functions that operate on individual types:

```haskell
f1 :: A1 -> B1
f2 :: A2 -> B2
```

We can create a function that operates on a tuple (A1, A2) by applying f1 and f2 to their respective components:

```haskell
import Control.Arrow (***)

f :: (A1, A2) -> (B1, B2)
f = f1 *** f2  -- Parallel composition using (***)
```

Here, `(***)` is an operator from the Control.Arrow module that applies `f1` to the first component and `f2` to the second component of a tuple simultaneously.

#### Practical Implications

1. **Modularity:** By viewing structured types as products, we can build complex functions from simpler ones, enhancing code modularity.

2. **Type Safety:** The use of product categories ensures that functions are composed in a type-safe manner, as the types of inputs and outputs are explicitly defined.

3. **Parallelism:** Parallel composition allows for potential parallel execution of functions operating on different components, improving performance.

#### Extending the Concept

- **Records and Named Fields:** Product categories can model records with named fields. Each field can be seen as a projection morphism, and functions can be composed over these fields in a similar fashion.

- **Nested Structures:** The concept extends to nested structured types. We can recursively apply product category principles to compose functions over nested data.

### c) Profunctor Optics

A more detailed look at how profunctors generalize lenses and prisms:

```haskell
import Data.Profunctor
import Data.Profunctor.Strong
import Data.Profunctor.Choice

-- Basic profunctor optic types
type Optic p s t a b = p a b -> p s t

-- Lens using profunctors
type Lens s t a b = forall p. Strong p => Optic p s t a b

-- Prism using profunctors
type Prism s t a b = forall p. Choice p => Optic p s t a b

-- Example of a custom profunctor for validation
data Validation e a b = Validation { runValidation :: a -> Either e b }

instance Profunctor (Validation e) where
    dimap f g (Validation h) = Validation $ \a -> fmap g (h (f a))

instance Choice (Validation e) where
    left' (Validation f) = Validation $ \case
        Left a  -> case f a of
            Left e  -> Left e
            Right b -> Right (Left b)
        Right c -> Right (Right c)
```

#### Practical Example with Profunctor Optics

```haskell
{-# LANGUAGE RankNTypes #-}

-- A more complex data structure
data User = User 
    { _userId   :: Int
    , _userInfo :: UserInfo 
    }

data UserInfo = UserInfo 
    { _email    :: Email
    , _settings :: Settings
    }

newtype Email = Email { getEmail :: String }
data Settings = Settings { _notifications :: Bool }

-- Define optics using profunctors
userInfo :: Lens' User UserInfo
userInfo = lens _userInfo (\u i -> u { _userInfo = i })

email :: Lens' UserInfo Email
email = lens _email (\i e -> i { _email = e })

-- Composing optics
userEmail :: Lens' User Email
userEmail = userInfo . email

-- Validation using profunctors
validateEmail :: Validation [String] String Email
validateEmail = Validation $ \s ->
    if isValidEmail s
        then Right (Email s)
        else Left ["Invalid email format"]

-- Using the validation
updateUserEmail :: String -> User -> Either [String] User
updateUserEmail newEmail user = 
    runValidation validateEmail newEmail 
        <&> \email' -> set userEmail email' user
```

This enhanced implementation shows how profunctors can be used to create type-safe and composable data accessors while maintaining validation and error handling capabilities.

### d) Monoidal and Applicative Composition

Monoids and applicative functors provide powerful abstractions for combining computations and results in functional programming. They enable the aggregation of multiple computations while maintaining code clarity and type safety.

#### Monoids

A **monoid** is an algebraic structure consisting of:
- An associative binary operation (`<>` or `mappend`): Combines two values of the monoid
- An identity element (`mempty`): Acts as a neutral element in the operation

```haskell
class Semigroup m => Monoid m where
    mempty  :: m
    -- mappend is often implicitly defined via (<>)
```

**Properties:**
- Associativity: `(a <> b) <> c = a <> (b <> c)`
- Identity: `mempty <> a = a` and `a <> mempty = a`

**Application in Composition:**
- Aggregating Results: Monoids allow us to combine the results of computations, such as concatenating lists, summing numbers, or merging maps
- Parallel Computation: Monoidal operations can be executed in parallel due to their associative property

**Example:**
```haskell
import Data.Monoid

sumNumbers :: [Int] -> Int
sumNumbers = getSum . mconcat . map Sum

-- Using different monoids for different aggregation strategies
data Stats = Stats { count :: Sum Int, total :: Sum Int }

instance Semigroup Stats where
    (Stats c1 t1) <> (Stats c2 t2) = Stats (c1 <> c2) (t1 <> t2)

instance Monoid Stats where
    mempty = Stats mempty mempty
```

#### Applicative Functors

An **applicative functor** allows for applying functions within a computational context to values within that context.

```haskell
class Functor f => Applicative f where
    pure  :: a -> f a
    (<*>) :: f (a -> b) -> f a -> f b
    liftA2 :: (a -> b -> c) -> f a -> f b -> f c  -- Derived operation
```

**Key Features:**
- Function Application: Lifted over the context, allowing us to apply functions to wrapped values
- Combining Contexts: Enables combining multiple computations that have effects or contexts
- Independent Computations: Perfect for scenarios where computations don't depend on each other's results

**Example with Validation:**
```haskell
import Data.Validation
import Data.Semigroup (Semigroup, (<>))

data UserData = UserData { name :: String, age :: Int }

validateName :: String -> Validation [String] String
validateName name 
    | length name < 2 = Failure ["Name too short"]
    | otherwise = Success name

validateAge :: Int -> Validation [String] Int
validateAge age
    | age < 0 = Failure ["Age cannot be negative"]
    | age > 150 = Failure ["Age unrealistic"]
    | otherwise = Success age

validateUser :: String -> Int -> Validation [String] UserData
validateUser name age = UserData 
    <$> validateName name 
    <*> validateAge age
```

#### Combining Monoids and Applicatives

We can leverage both concepts together for powerful data processing:

```haskell
-- Combining multiple validations with accumulated errors
data FormData = FormData {
    username :: String,
    email :: String,
    age :: Int
}

validateForm :: FormData -> Validation [String] FormData
validateForm form = FormData
    <$> validateUsername (username form)
    <*> validateEmail (email form)
    <*> validateAge (age form)
    where
        validateUsername = validateNonEmpty "username" >=> validateLength 3 20
        validateEmail = validateNonEmpty "email" >=> validateEmailFormat
```

#### Practical Applications

1. **Parallel Processing:**
```haskell
import Control.Parallel.Strategies

parallelComputation :: [a] -> [b]
parallelComputation = runEval . traverse (rpar . expensive)
  where expensive x = -- some costly computation
```

2. **Configuration Handling:**
```haskell
data Config = Config {
    port :: Int,
    host :: String,
    timeout :: Int
}

loadConfig :: IO (Validation [String] Config)
loadConfig = Config
    <$> readPort
    <*> readHost
    <*> readTimeout
```

3. **Data Aggregation:**
```haskell
data MetricSet = MetricSet {
    count :: Sum Int,
    average :: Average Double,
    errors :: [String]
}

instance Semigroup MetricSet where
    (MetricSet c1 a1 e1) <> (MetricSet c2 a2 e2) = 
        MetricSet (c1 <> c2) (a1 <> a2) (e1 <> e2)

instance Monoid MetricSet where
    mempty = MetricSet mempty mempty mempty
```

### e) Monad Transformers

Monad transformers enable the combination of multiple monadic effects into a single, unified computation. The order of transformers in the stack is crucial as it affects how effects interact.

#### Understanding Transformer Order

```haskell
import Control.Monad.Trans.State
import Control.Monad.Trans.Except
import Control.Monad.Trans.Reader
import Control.Monad.Trans.Writer
import Control.Monad.IO.Class

-- Different transformer orders have different semantics
type Stack1 = StateT State (ExceptT Error IO)    -- State changes persist after errors
type Stack2 = ExceptT Error (StateT State IO)    -- State changes are rolled back on errors

-- Example showing how transformer order affects behavior
example1 :: Stack1 a
example1 = do
    modify (+1)           -- State change happens
    throwError "Failed"   -- Error is thrown, but state change remains

example2 :: Stack2 a
example2 = do
    modify (+1)           -- State change happens
    throwError "Failed"   -- Error is thrown, state change is rolled back
```

#### Best Practices for Transformer Stacks

```haskell
-- Common transformer stack pattern
newtype AppM a = AppM {
    unAppM :: ReaderT Env (ExceptT Error (StateT State IO)) a
}

-- Helper functions for clean effect handling
runAppM :: Env -> State -> AppM a -> IO (Either Error (a, State))
runAppM env st app = 
    flip runStateT st                  -- Handle State
    . runExceptT                       -- Handle Errors
    . flip runReaderT env              -- Handle Environment
    . unAppM 
    $ app

-- Example of proper error handling with state management
data AppError 
    = ValidationError String
    | DatabaseError String
    | SystemError String
    deriving Show

data AppState = AppState {
    _counter :: !Int,        -- Strict field to prevent space leaks
    _cache :: !(Map.Map Key Value)  -- Strict Map for better performance
}

-- Function showing proper effect handling
complexOperation :: AppM Result
complexOperation = do
    -- Proper error handling with state management
    st <- get
    when (invalidState st) $
        throwError $ ValidationError "Invalid state"
    
    -- Safe database operation with error handling
    result <- dbOperation `catchError` \e -> do
        logError e        -- Log the error
        throwError $ DatabaseError (show e)
    
    -- Update state only on successful operations
    modify $ \s -> s { _counter = _counter s + 1 }
    return result
```

#### Performance Optimization

```haskell
-- Using strict fields to prevent space leaks
data StrictState = StrictState {
    _field1 :: !Int,
    _field2 :: !Text,
    _field3 :: !(Vector Double)
}

-- Efficient state updates
efficientUpdate :: StateT StrictState IO ()
efficientUpdate = do
    modify' $ \s -> s { _field1 = _field1 s + 1 }  -- Using modify' for strict updates
    
-- Batch operations for better performance
batchOperation :: StateT StrictState IO [Result]
batchOperation = do
    -- Process in chunks to maintain constant memory usage
    let chunks = chunksOf 1000 inputs
    foldM processChunk [] chunks
  where
    processChunk acc chunk = do
        results <- mapM processOne chunk
        return $! acc ++ results  -- Strict append
```

#### Handling Resource Cleanup

```haskell
-- Resource management with MonadMask
import Control.Monad.Catch

withResource :: (MonadMask m) => Resource -> (Resource -> m a) -> m a
withResource r action = bracket
    (acquireResource r)    -- Acquire
    releaseResource        -- Release (always runs)
    action                 -- Use resource

-- Example usage in transformer stack
resourceOperation :: AppM Result
resourceOperation = withResource someResource $ \r -> do
    -- Operations with resource
    result <- useResource r
    modify updateState
    return result
```

---

## 3. Practical Implementation Patterns

With the theoretical foundations in place, we can explore practical patterns for composing functions with structured data.

### Structured Data Composition Patterns

#### 1. Using Lenses for Focused Access and Updates

- Define lenses for each field or nested structure.
- Compose lenses to navigate complex data structures.
- Use `view`, `set`, and `over` for getting, setting, and modifying.

**Example:**

```haskell
-- Updating a nested field
updateNestedField :: (a -> a) -> OuterStructure -> OuterStructure
updateNestedField f = over (lens1 . lens2 . lens3) f
```

#### 2. Utilizing Functors and Applicatives

- Use `fmap` to apply functions over functorial structures.
- Use applicative operators `(<$>)` and `(<*>)` to combine computations.

**Example:**

```haskell
-- Applying functions over a list (Functor)
incrementList :: [Int] -> [Int]
incrementList = fmap (+1)

-- Combining computations (Applicative)
combineResults :: Maybe Int -> Maybe Int -> Maybe Int
combineResults x y = (+) <$> x <*> y
```

#### 3. Employing Profunctor Optics

- Define custom optics using profunctors for complex transformations.
- Utilize the flexibility of profunctors for specialized data access patterns.

#### 4. Leveraging Monoidal Composition

- Aggregate results using monoidal operations.
- Use `mconcat` to combine a list of monoidal values.

**Example:**

```haskell
-- Summing a list of numbers (Monoid instance for Sum)
import Data.Monoid

sumList :: [Int] -> Int
sumList = getSum . mconcat . map Sum
```

### Maintaining Type Safety

Strong type safety is crucial in functional programming.

#### Strategies:

- **Explicit Type Annotations:** Clarify function signatures.
- **Type Constraints in Composition:** Ensure composed functions are type-compatible.
- **Phantom Types:** Use to carry extra type information without affecting runtime.

**Example with Phantom Types:**

```haskell
data SafeValue a = SafeValue a

-- Function that requires a SafeValue
processSafe :: SafeValue Int -> Int
processSafe (SafeValue x) = x * 2
```

### Performance Considerations

#### Immutability vs. Mutability

- **Immutability Benefits:** Predictability, thread safety.
- **Mutability Trade-offs:** May improve performance in some cases.

#### Efficient Data Structures

- Use data structures optimized for functional updates (e.g., `Data.Sequence`).
- Avoid excessive copying by using persistent data structures.

#### Lazy Evaluation

- Leverage laziness to defer computations.
- Be cautious of space leaks due to unevaluated thunks.

**Example of Controlled Laziness:**
```haskell
import Control.DeepSeq

data Result = Result {
    _value :: !Int,    -- Strict field
    _cache :: [Int]    -- Lazy field
}

computeWithCache :: Int -> Result
computeWithCache n = Result value cache
  where
    value = sum [1..n]  -- Computed immediately
    cache = [1..n]      -- Computed only when needed

-- Force evaluation when needed
forceResult :: Result -> Result
forceResult = force
```

---

## 4. Parallelization over Subfields or List-like Attributes

Parallelization can significantly improve performance by leveraging concurrent computations.

### Applicative Functors for Parallelism

Applicative functors can model computations that can be performed in parallel.

#### Parallel Applicative

```haskell
import Control.Parallel.Strategies
import Control.Applicative

-- Assume f1 and f2 are independent computations
f1 :: Applicative f => f A
f2 :: Applicative f => f B

-- Run f1 and f2 in parallel and combine their results
combined :: Applicative f => f (A, B)
combined = (,) <$> f1 <*> f2

-- Practical example using parallel strategies
data ComplexData = ComplexData {
    field1 :: [Int],
    field2 :: [Double]
}

processParallel :: ComplexData -> ComplexData
processParallel cd = runEval $ do
    let f1' = map expensive1 (field1 cd)
    let f2' = map expensive2 (field2 cd)
    f1Eval <- rpar f1'
    f2Eval <- rpar f2'
    rseq f1Eval  -- Ensure evaluation before returning
    rseq f2Eval
    return $ ComplexData f1Eval f2Eval
  where
    expensive1 :: Int -> Int
    expensive1 x = x * x  -- CPU-intensive computation example
    
    expensive2 :: Double -> Double
    expensive2 x = x * log x  -- Another CPU-intensive computation example
```

### Traversals and Mapping

**Traversals** allow us to operate on elements within a structure that can be traversed, such as lists or trees.

#### Traversable Type Class

```haskell
class (Functor t, Foldable t) => Traversable t where
    traverse :: Applicative f => (a -> f b) -> t a -> f (t b)
    sequenceA :: Applicative f => t (f a) -> f (t a)
```

#### Example with Parallel Processing

```haskell
import Control.Parallel.Strategies

-- Process a list in parallel chunks
parallelChunks :: Int -> (a -> b) -> [a] -> [b]
parallelChunks n f xs = concat $ runEval $ do
    let chunks = splitIntoN n xs
    results <- mapM (rpar . map f) chunks
    return results
  where
    splitIntoN :: Int -> [a] -> [[a]]
    splitIntoN n xs = go xs
      where
        go [] = []
        go ys = take n ys : go (drop n ys)

-- Enhanced parallel computation using applicatives
parallelComputation :: (NFData a, NFData b) => IO a -> IO b -> IO (a, b)
parallelComputation ioA ioB = runEval $ do
    a <- rpar $ force $ ioA >>= evaluate . force  -- Incorrect: using rpar with IO
    b <- rpar $ force $ ioB >>= evaluate . force
    return (a, b)

-- Corrected version using proper concurrency primitives
import Control.Concurrent.Async (concurrently)

parallelComputation :: IO a -> IO b -> IO (a, b)
parallelComputation = concurrently  -- Correct: uses proper IO parallelism

-- Example of proper parallel IO operations
processParallelIO :: [IO a] -> IO [a]
processParallelIO actions = do
    asyncResults <- mapM async actions  -- Start all actions concurrently
    mapM wait asyncResults             -- Wait for all results

-- For pure computations, use evaluation strategies correctly
processParallelPure :: (NFData b) => [a] -> (a -> b) -> [b]
processParallelPure inputs f = runEval $ do
    let chunks = chunksOf 1000 inputs
    results <- mapM (rpar . force . map f) chunks  -- Proper use of force
    mapM_ rseq results
    return (concat results)
```

### Concurrency in Functional Programming

Haskell provides several abstractions for concurrency and parallelism.

#### Strategies and Evaluation Control

```haskell
import Control.Parallel.Strategies

data Result = Result Int [Int]

computeParallel :: [Int] -> Result
computeParallel xs = runEval $ do
    sum' <- rpar $ force $ sum xs
    prod' <- rpar $ force $ product xs
    return $ Result sum' (scanl1 (*) xs)

-- Using evaluation strategies
withStrategy :: Strategy a -> a -> a
withStrategy s x = runEval (s x)

parList :: Strategy a -> Strategy [a]
parList strat = traverse (rpar . strat)
```

#### Async Operations

```haskell
import Control.Concurrent.Async

-- Parallel processing with async
processDataAsync :: [Data] -> IO [Result]
processDataAsync inputs = do
    asyncResults <- mapM (async . processOne) inputs
    mapM wait asyncResults
  where
    processOne :: Data -> IO Result
    processOne = -- process single data item

-- Concurrent processing with timeout
timeoutProcess :: Int -> IO a -> IO (Maybe a)
timeoutProcess microseconds action = race (delay microseconds) action >>= \case
    Left _  -> return Nothing  -- timeout occurred
    Right x -> return (Just x)
  where
    delay n = threadDelay n
```

#### Software Transactional Memory (STM)

```haskell
import Control.Concurrent.STM

data SharedState = SharedState {
    counter :: TVar Int,
    cache   :: TVar (Map.Map Key Value)
}

-- Atomic operations on shared state
modifySharedState :: SharedState -> Key -> Value -> STM ()
modifySharedState state key value = do
    modifyTVar' (counter state) (+1)
    modifyTVar' (cache state) (Map.insert key value)

-- Running STM operations
updateState :: SharedState -> Key -> Value -> IO ()
updateState state key value = atomically $
    modifySharedState state key value
```

### Understanding Evaluation Strategies

Evaluation strategies provide fine-grained control over parallel evaluation:

```haskell
import Control.Parallel.Strategies
import Control.DeepSeq (NFData)

-- Basic strategy usage
data Result = Result Int [Int]

computeParallel :: [Int] -> Result
computeParallel xs = runEval $ do
    -- Explicitly control evaluation
    let sum'  = sum xs       -- Computation defined but not evaluated
    let prod' = product xs   -- Computation defined but not evaluated
    
    -- rpar: spark computation for parallel evaluation
    sumEval  <- rpar sum'    -- Spark sum computation
    prodEval <- rpar prod'   -- Spark product computation
    
    -- rseq: ensure evaluation before proceeding
    rseq sumEval             -- Wait for sum
    rseq prodEval           -- Wait for product
    
    return $ Result sumEval (scanl1 (*) xs)

-- Using parList for parallel list processing
parallelMap :: (NFData b) => (a -> b) -> [a] -> [b]
parallelMap f xs = withStrategy (parList rdeepseq) $ map f xs
```

Key Strategy Components:
- `rpar`: Sparks a computation for parallel evaluation
- `rseq`: Forces sequential evaluation
- `parList`: Strategy for parallel list processing
- `rdeepseq`: Evaluates structure completely (use when needed)

---

## 5. Deep Dive into Theoretical Concepts

Understanding the theoretical concepts strengthens our ability to apply them effectively.

### Categorical View

#### Category Theory Basics

A **category** consists of:

- **Objects:** Types in programming (e.g., Int, String, Maybe a)
- **Morphisms:** Functions between types
- **Composition:** Function composition with laws
- **Identity:** Identity function for each type

```haskell
import Control.Category
import Prelude hiding (id, (.))

-- Category laws in Haskell
-- 1. Identity:     id . f = f . id = f
-- 2. Associativity: (f . g) . h = f . (g . h)

-- Example category for functions
instance Category (->) where
    id x = x
    (f . g) x = f (g x)

-- Custom category example
data Transform a b = Transform (a -> b)

instance Category Transform where
    id = Transform (\x -> x)
    Transform f . Transform g = Transform (f . g)
```

#### Practical Category Examples

```haskell
-- Functor category
data DataFlow a b = DataFlow {
    transform :: a -> b,
    validate :: a -> Bool,
    cleanup  :: b -> b
}

instance Category DataFlow where
    id = DataFlow id (const True) id
    
    (DataFlow f1 v1 c1) . (DataFlow f2 v2 c2) = DataFlow
        { transform = c1 . f1 . f2
        , validate = \x -> v2 x && v1 (f2 x)
        , cleanup  = c1 . c2
        }

-- Example usage
processInt :: DataFlow Int Double
processInt = DataFlow
    { transform = fromIntegral
    , validate = (> 0)
    , cleanup = max 0.0
    }

processDouble :: DataFlow Double String
processDouble = DataFlow
    { transform = show
    , validate = not . isNaN
    , cleanup = take 10
    }

-- Composition creates a new transformation
processIntToString :: DataFlow Int String
processIntToString = processDouble . processInt
```

#### Functorial Properties with Examples

```haskell
-- Enhanced Functor example with laws
class BetterFunctor f where
    fmap' :: (a -> b) -> f a -> f b
    
    -- Laws:
    -- 1. Identity: fmap' id = id
    -- 2. Composition: fmap' (f . g) = fmap' f . fmap' g

-- Example implementation with validation
data Validated a = Invalid String | Valid a
    deriving Show

instance BetterFunctor Validated where
    fmap' _ (Invalid e) = Invalid e
    fmap' f (Valid x) = Valid (f x)

-- Practical usage
validateAndTransform :: (a -> Either String b) -> Validated a -> Validated b
validateAndTransform f (Valid x) = case f x of
    Left err -> Invalid err
    Right y  -> Valid y
validateAndTransform _ (Invalid e) = Invalid e

-- Example with natural transformations
type NatTrans f g = forall a. f a -> g a

maybeToValidated :: NatTrans Maybe Validated
maybeToValidated Nothing = Invalid "Value missing"
maybeToValidated (Just x) = Valid x
```

#### Categorical Composition Patterns

```haskell
-- Kleisli composition for monadic functions
import Control.Monad ((>=>))

type Kleisli m a b = a -> m b

validateInput :: Kleisli Maybe String Int
validateInput str = case reads str of
    [(n, "")] -> Just n
    _         -> Nothing

processInput :: Kleisli Maybe Int Double
processInput n 
    | n > 0     = Just (sqrt (fromIntegral n))
    | otherwise = Nothing

-- Compose validations using Kleisli composition
pipeline :: Kleisli Maybe String Double
pipeline = validateInput >=> processInput

-- Example with more complex compositions
data Pipeline i o = Pipeline {
    runPipe :: i -> Either String o,
    describe :: String
}

instance Category Pipeline where
    id = Pipeline Right "identity"
    Pipeline f1 d1 . Pipeline f2 d2 = Pipeline
        { runPipe = \x -> f2 x >>= f1
        , describe = d2 ++ " -> " ++ d1
        }
```

### Functorial Properties

#### Functors in Category Theory

A **functor** is a mapping between categories that preserves their structure. A functor F consists of:

- **Object Mapping:** Assigns to each object A in category C an object F(A) in category D.
- **Morphism Mapping:** Assigns to each morphism f: A -> B in C a morphism F(f): F(A) -> F(B) in D.

**Properties:**
- Preserves Composition: F(g ∘ f) = F(g) ∘ F(f)
- Preserves Identity Morphisms: F(id_A) = id_{F(A)}

#### Functors in Haskell

In Haskell, the Functor type class captures the essence of functors for types that can be mapped over:

```haskell
class Functor f where
    fmap :: (a -> b) -> f a -> f b
```

- `f` is a type constructor that takes a type a and produces a type f a
- `fmap` applies a function to a value within a context (e.g., Maybe, List)

#### Examples

```haskell
-- List Functor
instance Functor [] where
    fmap = map

-- Maybe Functor
instance Functor Maybe where
    fmap _ Nothing  = Nothing
    fmap f (Just x) = Just (f x)

-- Either Functor
instance Functor (Either e) where
    fmap _ (Left e) = Left e
    fmap f (Right x) = Right (f x)
```

#### Functor Laws

For a type to be a functor, it must satisfy two laws:

1. **Identity Law:**
```haskell
fmap id = id
```
Mapping the identity function over a functor should result in the original functor.

2. **Composition Law:**
```haskell
fmap (f . g) = fmap f . fmap g
```
Mapping a composition of functions is the same as composing the mappings.

#### Applications in Programming

1. **Abstraction over Data Structures:** Functors allow functions to operate over generic data structures without concerning themselves with the structure's specifics.

2. **Effectful Computations:** Functors enable the application of functions within contexts that represent computational effects (e.g., computations that may fail).

3. **Pipeline Processing:** By chaining fmap, we can create pipelines that transform data through a series of functions.

### Optic Theory

#### Lenses

A lens focuses on a specific part of a product type (e.g., a field in a record), allowing you to get or set that part.

```haskell
{-# LANGUAGE RankNTypes #-}
import Control.Lens

-- Van Laarhoven lens representation
type Lens s t a b = forall f. Functor f => (a -> f b) -> s -> f t
type Lens' s a = Lens s s a a  -- Simple lens (no type-changing)

-- Example data types
data User = User {
    _userId :: Int,
    _userProfile :: Profile
} deriving Show

data Profile = Profile {
    _name :: String,
    _email :: Email,
    _settings :: Settings
} deriving Show

data Settings = Settings {
    _notifications :: Bool,
    _theme :: Theme
} deriving Show

data Theme = Light | Dark deriving Show
newtype Email = Email String deriving Show

-- Lens definitions
makeLenses ''User
makeLenses ''Profile
makeLenses ''Settings

-- Manual lens definition example
userProfile :: Lens' User Profile
userProfile = lens _userProfile (\u p -> u { _userProfile = p })

-- Composing lenses
userEmail :: Lens' User Email
userEmail = userProfile . email

-- Practical usage
updateUserEmail :: String -> User -> User
updateUserEmail newEmail = over userEmail (\_ -> Email newEmail)

toggleTheme :: User -> User
toggleTheme = over (userProfile . settings . theme) $ \case
    Light -> Dark
    Dark -> Light
```

#### Prisms

Prisms are optics that focus on a single constructor of a sum type.

```haskell
-- Sum type example
data ApiResponse
    = Success { _data :: Value }
    | Error { _code :: Int, _message :: String }
    | Loading
    deriving Show

-- Prism definitions
_Success :: Prism' ApiResponse Value
_Success = prism Success $ \case
    Success d -> Right d
    x -> Left x

_Error :: Prism' ApiResponse (Int, String)
_Error = prism (uncurry Error) $ \case
    Error c m -> Right (c, m)
    x -> Left x

-- Practical usage
handleResponse :: ApiResponse -> String
handleResponse response = case matching _Success response of
    Right value -> "Got value: " ++ show value
    Left _ -> case matching _Error response of
        Right (code, msg) -> "Error " ++ show code ++ ": " ++ msg
        Left Loading -> "Loading..."
```

#### Traversals

Traversals allow you to focus on multiple elements within a structure.

```haskell
-- Example with nested structures
data Company = Company {
    _departments :: [Department],
    _locations :: [Location]
}

data Department = Department {
    _deptName :: String,
    _employees :: [Employee]
}

data Employee = Employee {
    _empName :: String,
    _salary :: Double
}

makeLenses ''Company
makeLenses ''Department
makeLenses ''Employee

-- Traversal to all employee salaries
allSalaries :: Traversal' Company Double
allSalaries = departments . traverse . employees . traverse . salary

-- Practical usage
increaseSalaries :: Double -> Company -> Company
increaseSalaries percentage = over allSalaries (* (1 + percentage / 100))

-- Combining traversals with filters
seniorEmployees :: Traversal' Company Employee
seniorEmployees = departments . traverse . employees . traverse . filtered isSenior
  where
    isSenior emp = _salary emp > 100000

-- Complex traversal example
data NestedData = NestedData {
    _level1 :: [Level1]
} deriving Show

data Level1 = Level1 {
    _name :: String,
    _level2 :: [Level2]
} deriving Show

data Level2 = Level2 {
    _value :: Int,
    _active :: Bool
} deriving Show

makeLenses ''NestedData
makeLenses ''Level1
makeLenses ''Level2

-- Traversal to all active level2 values
activeValues :: Traversal' NestedData Int
activeValues = level1 . traverse . level2 . traverse . 
               filtered _active . value

-- Usage example
updateActiveValues :: (Int -> Int) -> NestedData -> NestedData
updateActiveValues f = over activeValues f
```

#### Optic Composition Patterns

```haskell
-- Combining different types of optics
type UserLens = Lens' User Profile
type ProfilePrism = Prism' Profile Settings
type SettingsTraversal = Traversal' Settings Theme

-- Complex composition
complexOptic :: Traversal' User Theme
complexOptic = userProfile                     -- Lens
            . _Just                            -- Prism
            . settings                         -- Lens
            . filtered isValidSettings         -- Traversal
            . theme                           -- Lens
  where
    isValidSettings s = _notifications s       -- Validation

-- Practical application
updateThemes :: (Theme -> Theme) -> User -> User
updateThemes f = over complexOptic f
```

### Monads and Applicatives

Monads and applicative functors are key abstractions in functional programming that handle computations with context, such as side effects, uncertainty, or dependencies between operations.

#### Monads

A monad enables the sequencing of computations where each step may depend on the result of the previous one.

```haskell
class Applicative m => Monad m where
    (>>=)  :: m a -> (a -> m b) -> m b
    return :: a -> m a  -- return is equivalent to pure
```

**Key Characteristics:**
- Dependent Computations: Each computation can use the result of the previous one
- Chaining Operations: Monads allow for clean chaining of operations that involve context

**Example:**
```haskell
-- Using Maybe monad to handle computations that may fail
safeDivide :: Double -> Double -> Maybe Double
safeDivide _ 0 = Nothing
safeDivide x y = Just (x / y)

computeResult :: Maybe Double
computeResult = do
    x <- Just 10
    y <- Just 2
    safeDivide x y  -- Results in Just 5.0
```

#### Monad Laws

Monads must satisfy three laws to ensure consistent behavior:

1. **Left Identity:**
```haskell
return a >>= f = f a
```

2. **Right Identity:**
```haskell
m >>= return = m
```

3. **Associativity:**
```haskell
(m >>= f) >>= g = m >>= (\x -> f x >>= g)
```

#### Applicatives vs. Monads

**Applicative Functors:**
- Simpler abstraction
- Cannot express dependencies between computations
- Potential for parallelism due to independent computations

**Monads:**
- More powerful abstraction
- Can express dependencies between computations
- Sequential execution due to dependencies

#### Monoidal Categories

In category theory, a monoidal category is a category equipped with:
- A tensor product (⊗)
- A unit object I
- Satisfying certain coherence conditions

**In Programming:** The concept relates to how we can combine data or computations in a structured way, often using monoids or applicative functors.

#### Example Applications

```haskell
-- Combining Maybe values with Applicative
data User = User { name :: String, age :: Int }

validateUser :: String -> Int -> Maybe User
validateUser name age = User 
    <$> validateName name 
    <*> validateAge age
  where
    validateName n = if null n then Nothing else Just n
    validateAge a = if a < 0 then Nothing else Just a

-- Monadic composition for dependent operations
type DatabaseM = ExceptT String IO

getUserData :: UserId -> DatabaseM UserData
getUserData uid = do
    user <- queryUser uid        -- First operation
    perms <- queryPermissions uid -- Depends on first operation
    return $ UserData user perms
```

#### Applicatives vs. Monads (continued)

**Applicative Functors:**
- Simpler abstraction
- Cannot express dependencies between computations
- Potential for parallelism due to independent computations

```haskell
-- Applicative style
data Form = Form { name :: String, age :: Int, email :: String }

validateForm :: Form -> Validation [String] Form
validateForm form = Form
    <$> validateName (name form)
    <*> validateAge (age form)
    <*> validateEmail (email form)

-- All validations run independently
```

**Monads:**
- More powerful abstraction
- Can express dependencies between computations
- Sequential execution due to dependencies

```haskell
-- Monadic style with dependencies
processUserData :: User -> IO (Either Error Result)
processUserData user = runExceptT $ do
    profile <- loadProfile user        -- Must run first
    permissions <- checkPermissions profile  -- Depends on profile
    settings <- loadSettings permissions     -- Depends on permissions
    return $ createResult profile permissions settings
```

#### Advanced Monad Patterns

```haskell
-- Monad transformers for complex computations
type AppMonad = ReaderT Config (ExceptT ValidationError (StateT AppState IO))

-- Kleisli arrows for composing monadic functions
type Handler a b = a -> AppMonad b

validateUser :: Handler User ValidUser
validateUser user = do
    config <- ask
    when (userAge user < minAge config) $
        throwError "User too young"
    return $ ValidUser user

processUser :: Handler ValidUser ProcessedUser
processUser validUser = do
    state <- get
    let result = performProcessing validUser state
    put $ updateState state
    return result

-- Compose handlers using Kleisli composition
pipeline :: Handler User ProcessedUser
pipeline = validateUser >=> processUser

-- Free monads for extensible effects
data ProgramF next
    = LogMessage String next
    | GetConfig (Config -> next)
    | SaveData DataRecord next
    deriving Functor

type Program = Free ProgramF

-- Smart constructors
logMessage :: String -> Program ()
logMessage msg = liftF $ LogMessage msg ()

getConfig :: Program Config
getConfig = liftF $ GetConfig id

saveData :: DataRecord -> Program ()
saveData data' = liftF $ SaveData data' ()
```

## 7. Conclusion

This exploration of function composition with structured data types has covered several key aspects:

1. **Theoretical Foundations**
   - Category theory provides a mathematical framework for composition
   - Functors, applicatives, and monads offer structured ways to handle effects
   - Optics provide principled approaches to data access and modification

2. **Practical Implementations**
   - Lenses and prisms for working with nested data
   - Monad transformers for combining effects
   - Parallel processing capabilities through applicative functors

3. **Performance Considerations**
   - Proper use of evaluation strategies
   - Memory efficiency through strict fields
   - Parallel and concurrent execution patterns

4. **Best Practices**
   - Type-safe composition patterns
   - Error handling strategies
   - Resource management techniques

The combination of these aspects enables developers to write code that is:
- Type-safe and maintainable
- Performant and scalable
- Composable and reusable

## 8. References

1. **Category Theory**
   - "Category Theory for Programmers" by Bartosz Milewski
   - "Basic Category Theory for Computer Scientists" by Benjamin C. Pierce

2. **Functional Programming**
   - "Thinking with Types" by Sandy Maguire
   - "Parallel and Concurrent Programming in Haskell" by Simon Marlow

3. **Optics**
   - "Optics By Example" by Chris Penner
   - "Profunctor Optics: Modular Data Accessors" by Matthew Pickering

4. **Performance**
   - "Parallel and Concurrent Programming in Haskell" by Simon Marlow
   - "Real World Haskell" by Bryan O'Sullivan

5. **Online Resources**
   - [Haskell Wiki](https://wiki.haskell.org)
   - [Lens Package Documentation](https://hackage.haskell.org/package/lens)
   - [GHC User Guide: Parallel and Concurrent Programming](https://downloads.haskell.org/ghc/latest/docs/html/users_guide/parallel.html)

### Helper Functions and Type Definitions

```haskell
{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE StrictData #-}
{-# LANGUAGE TemplateHaskell #-}
{-# LANGUAGE FlexibleContexts #-}
{-# LANGUAGE RankNTypes #-}
{-# LANGUAGE MultiParamTypeClasses #-}
{-# LANGUAGE FunctionalDependencies #-}

import qualified Data.Text as T
import Data.Time (UTCTime, getCurrentTime)
import qualified Data.Map as Map
import Control.Monad.IO.Class
import Control.Exception (evaluate)
import GHC.Generics (Generic)
import Control.DeepSeq (NFData)
import Data.Aeson (FromJSON, ToJSON)
import Control.Concurrent.Async (concurrently, async, wait)
import Control.Lens
import Control.Monad.Free

-- Basic types
type Key = T.Text
type Value = T.Text

data ValidationError 
    = InvalidInput String
    | InvalidFormat String
    | SystemError String
    deriving (Show, Eq, Generic)

instance NFData ValidationError

-- Data type for Free Monad example
data DataRecord = DataRecord
    { dataId :: Int
    , dataContent :: T.Text
    } deriving (Show, Eq, Generic)

instance NFData DataRecord

-- Helper for email validation
isValidEmail :: T.Text -> Bool
isValidEmail email = 
    T.length email > 3 && 
    T.any (== '@') email && 
    T.any (== '.') (T.dropWhile (/= '@') email)

-- Helper for input validation
validateNonEmpty :: T.Text -> T.Text -> Either ValidationError T.Text
validateNonEmpty fieldName value
    | T.null value = Left $ InvalidInput $ "Field " <> T.unpack fieldName <> " cannot be empty"
    | otherwise = Right value

validateLength :: Int -> Int -> T.Text -> Either ValidationError T.Text
validateLength min max value
    | len < min = Left $ InvalidFormat $ "Length must be at least " <> show min
    | len > max = Left $ InvalidFormat $ "Length must be at most " <> show max
    | otherwise = Right value
  where len = T.length value

-- State validation helpers
data AppState = AppState 
    { stateCounter :: !Int
    , stateData :: !(Map.Map Key Value)
    , stateLastUpdate :: !UTCTime
    , stateValid :: !Bool
    } deriving (Show, Eq, Generic)

instance NFData AppState

-- Resource management (corrected order)
data ResourceHandle = ResourceHandle 
    { handleId :: !Int
    , handleActive :: !Bool
    } deriving (Show)

data Resource = Resource 
    { resourceId :: !Int
    , resourceType :: !T.Text
    , resourceHandle :: !ResourceHandle
    } deriving (Show)

-- Monad transformer stack with defined Error type
type AppMonad = ReaderT Config (ExceptT ValidationError (StateT AppState IO))

-- Free monad definitions with concrete Data type
data ProgramF next
    = LogMessage String next
    | GetConfig (Config -> next)
    | SaveData DataRecord next
    deriving Functor

type Program = Free ProgramF

-- Smart constructors
logMessage :: String -> Program ()
logMessage msg = liftF $ LogMessage msg ()

getConfig :: Program Config
getConfig = liftF $ GetConfig id

saveData :: DataRecord -> Program ()
saveData data' = liftF $ SaveData data' ()

-- Resource management
acquireResource :: T.Text -> IO Resource
acquireResource resType = do
    let handle = ResourceHandle 1 True
    return $ Resource 1 resType handle

releaseResource :: Resource -> IO ()
releaseResource res = do
    liftIO $ putStrLn $ "Releasing resource: " <> show (resourceId res)
    return ()

-- Chunking helper for parallel processing
chunksOf :: Int -> [a] -> [[a]]
chunksOf n = go
  where
    go [] = []
    go xs = let (chunk, rest) = splitAt n xs
            in chunk : go rest

-- Strict evaluation helper
forceEither :: (NFData a, NFData e) => Either e a -> Either e a
forceEither (Left e) = e `deepseq` Left e
forceEither (Right x) = x `deepseq` Right x

-- Database operation simulation
data DbError = DbConnectionError String | DbQueryError String
    deriving (Show, Eq)

dbOperation :: AppState -> IO (Either DbError ProcessedResult)
dbOperation state = do
    if stateValid state
        then Right <$> performProcessing state
        else return $ Left $ DbQueryError "Invalid state"

-- Logging helpers
data LogLevel = Debug | Info | Warn | Error
    deriving (Show, Eq, Ord)

logError :: MonadIO m => String -> m ()
logError msg = liftIO $ putStrLn $ "[ERROR] " <> msg

logInfo :: MonadIO m => String -> m ()
logInfo msg = liftIO $ putStrLn $ "[INFO] " <> msg

-- Configuration helpers
data Config = Config 
    { configPort :: !Int
    , configHost :: !T.Text
    , configTimeout :: !Int
    , configMaxRetries :: !Int
    } deriving (Show, Eq, Generic)

instance NFData Config

defaultConfig :: Config
defaultConfig = Config 
    { configPort = 8080
    , configHost = "localhost"
    , configTimeout = 5000
    , configMaxRetries = 3
    }